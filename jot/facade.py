from contextlib import contextmanager as _contextmanager

from .base import Telemeter

active = Telemeter()


def _swap_active(new_active):
    global active
    old_active = active
    active = new_active
    return old_active


def start(*args, **kwargs):
    return active.start(*args, **kwargs)


def finish(*args, **kwargs):
    return active.finish(*args, **kwargs)


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
def span(name, /, *, trace_id=None, parent_id=None, **kwtags):
    child = active.start(name, trace_id=trace_id, parent_id=parent_id, **kwtags)
    parent = _swap_active(child)
    try:
        yield child
    except Exception as exc:
        child.error(f"Error during {name}", exc)
        raise exc
    finally:
        child.finish()
        _swap_active(parent)
