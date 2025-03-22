from contextlib import contextmanager as _contextmanager

from .base import Meter

active_meter = Meter()


def _swap_active(new_active):
    global active_meter
    old_active = active_meter
    active_meter = new_active
    return old_active


def start(*args, **kwargs):
    return active_meter.start(*args, **kwargs)


def finish(*args, **kwargs):
    return active_meter.finish(*args, **kwargs)


def event(*args, **kwargs):
    return active_meter.event(*args, **kwargs)


def debug(*args, **kwargs):
    return active_meter.debug(*args, **kwargs)


def info(*args, **kwargs):
    return active_meter.info(*args, **kwargs)


def warning(*args, **kwargs):
    return active_meter.warning(*args, **kwargs)


def error(*args, **kwargs):
    return active_meter.error(*args, **kwargs)


def magnitude(*args, **kwargs):
    return active_meter.magnitude(*args, **kwargs)


def count(*args, **kwargs):
    return active_meter.count(*args, **kwargs)


@_contextmanager
def span(name, /, *, trace_id=None, parent_id=None, **kwtags):
    child = active_meter.start(name, trace_id=trace_id, parent_id=parent_id, **kwtags)
    parent = _swap_active(child)
    try:
        yield child
    except Exception as exc:
        child.error(f"Error during {name}", exc)
        raise exc
    finally:
        child.finish()
        _swap_active(parent)
