from .base import Meter

active_meter = Meter()


def _swap_active(new_active):
    global active_meter
    old_active = active_meter
    active_meter = new_active
    return old_active


def generate_trace_id():
    return active_meter.target.generate_trace_id()


def span(*args, **kwargs):
    return active_meter.span(*args, **kwargs)


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
