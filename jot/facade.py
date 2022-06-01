import sys
from contextlib import contextmanager as _contextmanager

from .base import Telemeter

active = Telemeter()
stack = []


def _push(telemeter):
    global active
    stack.append(active)
    active = telemeter


def _pop():
    global active
    active = stack.pop()


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
