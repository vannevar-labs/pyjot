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
        try:
            coro = func(*args, **kwargs)
            child.start()
            try:
                future = coro.send(None)
                _facade._swap_active(parent)
                while True:
                    value = None
                    if future:
                        await asyncio.wait([future])
                        exc = future.exception()
                        if exc:
                            _facade._swap_active(child)
                            future = coro.throw(exc)
                            _facade._swap_active(parent)
                            continue

                    _facade._swap_active(child)
                    future = coro.send(value)
                    _facade._swap_active(parent)

            except StopIteration as e:
                return e.value

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
