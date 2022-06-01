import functools
from inspect import Parameter, signature
import warnings

from . import facade as _facade


def generator(name, **static_tags):
    def decorator(func):

        # first create the wrapper
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # extract tags from the keyword arguments
            tags = static_tags.copy()
            for tag_name in tag_names_to_extract(kwargs):
                tags[tag_name] = kwargs.pop(tag_name)

            # start a new span, which will be active while the generator is running
            captured = _facade.active.start(name, **tags)

            # run the generator
            # TODO: log errors raised within the generator
            it = func(*args, **kwargs)
            try:
                while True:
                    current = _facade.active
                    _facade.active = captured
                    val = next(it)
                    _facade.active = current
                    yield val
            except StopIteration:
                captured.finish()
            finally:
                _facade.active = current

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
