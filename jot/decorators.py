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
        elif inspect.isasyncgenfunction(func):
            return wrap_async_generator(func, dtags, stags)
        elif inspect.isgeneratorfunction(func):
            return wrap_sync_generator(func, dtags, stags)

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
                        elif exception := future.exception():
                            future = inject_exception(coro, exception)
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


def wrap_sync_generator(func, dynamic_tag_names, static_tags):
    name = func.__name__

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tags = extract_tags(dynamic_tag_names, static_tags, kwargs)

        # Create the generator
        generator = func(*args, **kwargs)

        # Wrap it with instrumentation
        return InstrumentedSyncGenerator(generator, name, tags)

    return wrapper


def wrap_async_generator(func, dynamic_tag_names, static_tags):
    name = func.__name__

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tags = extract_tags(dynamic_tag_names, static_tags, kwargs)

        # Create the async generator
        async_generator = func(*args, **kwargs)

        # Wrap it with instrumentation
        return InstrumentedAsyncGenerator(async_generator, name, tags)

    return wrapper


class InstrumentedSyncGenerator:
    def __init__(self, generator, name, tags):
        self.generator = generator
        self.name = name
        self.tags = tags
        self.child = None
        self.parent = None
        self._started = False

    def __iter__(self):
        return self

    def __next__(self):
        if not self._started:
            self._start_span()

        try:
            self._activate_span()
            value = next(self.generator)
            self._deactivate_span()
            return value
        except StopIteration:
            self._finish_span()
            raise
        except Exception as e:
            self._handle_error(e)
            raise

    def close(self):
        try:
            self.generator.close()
        finally:
            if self._started:
                self._finish_span()

    def send(self, value):
        if not self._started:
            self._start_span()

        try:
            self._activate_span()
            result = self.generator.send(value)
            self._deactivate_span()
            return result
        except StopIteration:
            self._finish_span()
            raise
        except Exception as e:
            self._handle_error(e)
            raise

    def throw(self, typ, val=None, tb=None):
        if not self._started:
            self._start_span()

        try:
            self._activate_span()
            result = self.generator.throw(typ, val, tb)
            self._deactivate_span()
            return result
        except StopIteration:
            self._finish_span()
            raise
        except Exception as e:
            self._handle_error(e)
            raise

    def _start_span(self):
        self.child = _facade.active_meter.start(self.name, **self.tags)
        self.parent = _facade._swap_active(self.child)
        self._started = True

    def _activate_span(self):
        _facade._swap_active(self.child)

    def _deactivate_span(self):
        _facade._swap_active(self.parent)

    def _finish_span(self):
        if self._started and self.child is not None:
            _facade._swap_active(self.parent)
            self.child.finish()
            self._started = False

    def _handle_error(self, exception):
        if self._started and self.child is not None:
            self.child.error(f"Error during {self.name}", exception)
            self._finish_span()


class InstrumentedAsyncGenerator:
    def __init__(self, async_generator, name, tags):
        self.async_generator = async_generator
        self.name = name
        self.tags = tags
        self.child = None
        self.parent = None
        self._started = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._started:
            self._start_span()

        try:
            self._activate_span()
            value = await self.async_generator.__anext__()
            self._deactivate_span()
            return value
        except StopAsyncIteration:
            self._finish_span()
            raise
        except Exception as e:
            self._handle_error(e)
            raise

    async def aclose(self):
        try:
            await self.async_generator.aclose()
        finally:
            if self._started:
                self._finish_span()

    async def asend(self, value):
        if not self._started:
            self._start_span()

        try:
            self._activate_span()
            result = await self.async_generator.asend(value)
            self._deactivate_span()
            return result
        except StopAsyncIteration:
            self._finish_span()
            raise
        except Exception as e:
            self._handle_error(e)
            raise

    async def athrow(self, typ, val=None, tb=None):
        if not self._started:
            self._start_span()

        try:
            self._activate_span()
            result = await self.async_generator.athrow(typ, val, tb)
            self._deactivate_span()
            return result
        except StopAsyncIteration:
            self._finish_span()
            raise
        except Exception as e:
            self._handle_error(e)
            raise

    def _start_span(self):
        self.child = _facade.active_meter.start(self.name, **self.tags)
        self.parent = _facade._swap_active(self.child)
        self._started = True

    def _activate_span(self):
        _facade._swap_active(self.child)

    def _deactivate_span(self):
        _facade._swap_active(self.parent)

    def _finish_span(self):
        if self._started and self.child is not None:
            _facade._swap_active(self.parent)
            self.child.finish()
            self._started = False

    def _handle_error(self, exception):
        if self._started and self.child is not None:
            self.child.error(f"Error during {self.name}", exception)
            self._finish_span()


def extract_tags(dynamic_tag_names, static_tags, keyword_args):
    tags = copy(static_tags)
    for tag_name in dynamic_tag_names:
        if tag_name in keyword_args:
            tags[tag_name] = keyword_args.pop(tag_name)
    return tags
