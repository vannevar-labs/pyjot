from .base import Meter, TraceContext

active_meter = Meter()


def _swap_active(new_active):
    global active_meter
    old_active = active_meter
    active_meter = new_active
    return old_active


def get_trace_context():
    if active_meter.active_span is None:
        return None

    return TraceContext(
        trace_id=active_meter.active_span.trace_id,
        parent_id=active_meter.active_span.id,
    )


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
