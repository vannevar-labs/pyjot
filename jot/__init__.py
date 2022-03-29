import functools
from contextlib import contextmanager as _contextmanager
from inspect import Parameter, signature
import warnings

from .telemeter import Telemeter

active = Telemeter()
_stack = []


def _push(telemeter):
    global active
    _stack.append(active)
    active = telemeter


def _pop():
    global active
    active = _stack.pop()


def init(target, dtags={}, **kwtags):
    global active, _stack
    active = Telemeter(target, None, dtags, **kwtags)
    _stack = []


def start(*args, **kwargs):
    child = active.start(*args, **kwargs)
    _push(child)


def finish(*args, **kwargs):
    active.finish(*args, **kwargs)
    _pop()


def event(*args, **kwargs):
    return active.event(*args, **kwargs)


def debug(*args, **kwargs):
    return active.debug(*args, **kwargs)


def info(*args, **kwargs):
    return active.info(*args, **kwargs)


def warning(*args, **kwargs):
    return active.warning(*args, **kwargs)


def error(*args, **kwargs):
    return active.error(*args, **kwargs)


def magnitude(*args, **kwargs):
    return active.magnitude(*args, **kwargs)


def count(*args, **kwargs):
    return active.count(*args, **kwargs)


@_contextmanager
def span(name, trace_id=None, parent_id=None, **tags):
    if trace_id is None:
        child = active.start(name, **tags)
    else:
        span = active.target.span(trace_id=trace_id, parent_id=parent_id, name=name)
        child = Telemeter(active.target, span, **tags)
    _push(child)

    try:
        yield child
    except Exception as exc:
        child.error(f"Error during {name}", exc)
        raise exc
    finally:
        child.finish()
        _pop()


def generator(name, **static_tags):
    def decorator(func):

        # first create the wrapper
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            global active

            # extract tags from the keyword arguments
            tags = static_tags.copy()
            for tag_name in tag_names_to_extract(kwargs):
                tags[tag_name] = kwargs.pop(tag_name)

            # start a new span, which will be active while the generator is running
            captured = active.start(name, **tags)

            # run the generator
            # TODO: log errors raised within the generator
            it = func(*args, **kwargs)
            try:
                while True:
                    current = active
                    active = captured
                    val = next(it)
                    active = current
                    yield val
            except StopIteration:
                captured.finish()
            finally:
                active = current

        # the @tag decorator will add tag names to this whitelist
        wrapper._uses_whitelist = False
        wrapper._whitelist = []

        # introspect on the generator function to figure out how to extract tags
        sig = signature(func)
        if _is_positional_only(sig):
            # the simple case
            def tag_names_to_extract(kwargs):
                return list(kwargs.keys())

        elif _has_kwargs(sig):
            # the generator function can accept any keyword argument, so we only extract
            # tags based on the whitelist explicitly supplied via the @tag decorator
            wrapper._uses_whitelist = True

            def tag_names_to_extract(kwargs):
                return [n for n in kwargs.keys() if n in wrapper._whitelist]

        else:
            # the generator function accepts only specific keyword arguments, so we blacklist them
            # any keyword argument that is not on the blacklist will be treated as a tag
            blacklist = [p.name for p in sig.parameters.values() if _could_be_keyword(p.kind)]

            def tag_names_to_extract(kwargs):
                return [n for n in kwargs.keys() if n not in blacklist]

        return wrapper

    return decorator


def tag(name):
    def decorator(func):
        if not hasattr(func, "_whitelist"):
            raise RuntimeError(f"{func.__name__}() isn't decorated by jot")

        if not func._uses_whitelist:
            warnings.warn(f"{func.__name__}() doesn't need tag decorations", UserWarning)

        func._whitelist.append(name)
        return func

    return decorator


def _could_be_keyword(kind):
    if kind == Parameter.POSITIONAL_OR_KEYWORD:
        return True
    if kind == Parameter.KEYWORD_ONLY:
        return True
    if kind == Parameter.VAR_KEYWORD:
        return True
    return False


def _is_positional_only(sig):
    return not any(_could_be_keyword(p.kind) for p in sig.parameters.values())


def _has_kwargs(sig):
    return any(p.kind == Parameter.VAR_KEYWORD for p in sig.parameters.values())


### TODO: decorator for coroutines
### TODO: decorator for functions
