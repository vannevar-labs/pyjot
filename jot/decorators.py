import asyncio
import functools
import inspect
from copy import copy

from . import facade as _facade


def instrument(*dtags, **stags):
    if len(dtags) == 1 and callable(dtags[0]):
        # Uncalled decorator
        return make_decorator([], {})(dtags[0])

    # Called decorator
    return make_decorator(dtags, stags)


def make_decorator(dtags, stags):
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            return wrap_async(func, dtags, stags)

        return wrap_sync(func, dtags, stags)

    return decorator


def wrap_async(func, dynamic_tag_names, static_tags):
    name = func.__name__

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tags = extract_tags(dynamic_tag_names, static_tags, kwargs)
        child = _facade.active_meter.span(name, **tags)
        parent = _facade._swap_active(child)

        def inject_exception(coro, exception):
            _facade._swap_active(child)
            try:
                result = coro.throw(exception)
                _facade._swap_active(parent)
                return result
            except StopIteration:
                # Coroutine completed, return the result
                _facade._swap_active(parent)
                raise
            except asyncio.CancelledError:
                # Coroutine didn't handle the cancellation, let it bubble up
                _facade._swap_active(parent)
                raise

        def advance_coro(coro, value):
            _facade._swap_active(child)
            try:
                result = coro.send(value)
                _facade._swap_active(parent)
                return result
            except StopIteration:
                _facade._swap_active(parent)
                raise

        try:
            coro = func(*args, **kwargs)
            child.start()
            try:
                # Start the coroutine
                future = advance_coro(coro, None)

                while True:
                    if future:
                        # Wait for the future and handle cancellation
                        try:
                            await asyncio.wait([future])
                        except asyncio.CancelledError as cancel_error:
                            # Inject cancellation into the coroutine
                            future = inject_exception(coro, cancel_error)
                            continue

                        # Process the completed future
                        if future.cancelled():
                            future = inject_exception(coro, asyncio.CancelledError())
                        elif future.exception():
                            future = inject_exception(coro, future.exception())
                        else:
                            # Send the result to the coroutine
                            future = advance_coro(coro, future.result())
                    else:
                        # No future to wait for, just advance with None
                        future = advance_coro(coro, None)

            except StopIteration as e:
                return e.value

        except asyncio.CancelledError:
            # Don't log cancellation as an error
            raise
        except Exception as e:
            child.error(f"Error during {name}", e)
            raise
        finally:
            _facade._swap_active(parent)
            child.finish()

    return wrapper


def wrap_sync(func, dynamic_tag_names, static_tags):
    name = func.__name__

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tags = extract_tags(dynamic_tag_names, static_tags, kwargs)
        child = _facade.active_meter.start(name, **tags)
        parent = _facade._swap_active(child)
        try:
            return func(*args, **kwargs)

        except Exception as e:
            child.error(f"Error during {name}", e)
            raise

        finally:
            _facade._swap_active(parent)
            child.finish()

    return wrapper


def extract_tags(dynamic_tag_names, static_tags, keyword_args):
    tags = copy(static_tags)
    for tag_name in dynamic_tag_names:
        if tag_name in keyword_args:
            tags[tag_name] = keyword_args.pop(tag_name)
    return tags
