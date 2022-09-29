import random
from time import monotonic_ns, time_ns

from jot.util import hex_encode as _hex_encode

from . import log


class Telemeter:
    """The instrumentation interface"""

    def __init__(self, target=None, span=None, dtags={}, **kwtags) -> None:
        self.target = target if target is not None else Target()
        self.span = span
        self.tags = {**dtags, **kwtags}

    """Tracing Methods"""

    def start(self, name, dtags={}, trace_id=None, parent_id=None, **kwtags):
        tags = {**self.tags, **dtags, **kwtags}
        if trace_id is not None:
            trace_id = trace_id
            parent_id = parent_id
        elif self.span is not None:
            trace_id = self.span.trace_id
            parent_id = self.span.id
        else:
            trace_id = None
            parent_id = None
        span = self.target.start(trace_id, parent_id, name=name)
        return Telemeter(self.target, span, **tags)

    def finish(self, dtags={}, **kwtags):
        tags = {**self.tags, **dtags, **kwtags}
        self.span.finish()
        self.target.finish(tags, self.span)

    def event(self, name, dtags={}, **kwtags):
        tags = {**self.tags, **dtags, **kwtags}
        self.target.event(name, tags, self.span)

    """Logging methods"""

    def debug(self, message, dtags={}, **kwtags):
        if self.target.accepts_log_level(log.DEBUG):
            tags = {**self.tags, **dtags, **kwtags}
            self.target.log(log.DEBUG, message, tags, self.span)

    def info(self, message, dtags={}, **kwtags):
        if self.target.accepts_log_level(log.INFO):
            tags = {**self.tags, **dtags, **kwtags}
            self.target.log(log.INFO, message, tags, self.span)

    def warning(self, message, dtags={}, **kwtags):
        if self.target.accepts_log_level(log.WARNING):
            tags = {**self.tags, **dtags, **kwtags}
            self.target.log(log.WARNING, message, tags, self.span)

    """Error methods"""

    def error(self, message, exception, dtags={}, **kwtags):
        tags = {**self.tags, **dtags, **kwtags}
        self.target.error(message, exception, tags, self.span)

    """Metrics methods"""

    def magnitude(self, name, value, dtags={}, **kwtags):
        # TODO: check that value is a number
        tags = {**self.tags, **dtags, **kwtags}
        self.target.magnitude(name, value, tags, self.span)

    def count(self, name, value, dtags={}, **kwtags):
        # TODO: check that value is an integer
        tags = {**self.tags, **dtags, **kwtags}
        self.target.count(name, value, tags, self.span)


class Event:
    def __init__(self, name, timestamp=None, tags={}):
        self.name = name
        self.timestamp = timestamp if timestamp else time_ns()
        self.tags = tags


class Span:
    @classmethod
    def _gen_id(cls, byte_count):
        return bytes(random.getrandbits(8) for _ in range(byte_count))

    @classmethod
    def gen_trace_id(cls):
        return cls._gen_id(16)

    @classmethod
    def gen_span_id(cls):
        return cls._gen_id(8)

    @classmethod
    def from_parent(cls, parent, name=None):
        trace_id = parent.trace_id if parent else None
        parent_id = parent.id if parent else None
        return cls(trace_id, parent_id, name=name)

    def __init__(self, trace_id=None, parent_id=None, id=None, name=None):
        self.trace_id = trace_id if trace_id else self.gen_trace_id()
        self.parent_id = parent_id
        self.id = id if id else self.gen_span_id()
        self.name = name
        self.events = []
        self.baggage = {}
        self.start()

    #
    # ids
    #
    @property
    def trace_id_hex(self):
        return _hex_encode(self.trace_id)

    @property
    def parent_id_hex(self):
        return _hex_encode(self.parent_id)

    @property
    def id_hex(self):
        return _hex_encode(self.id)

    #
    # timing
    #
    def start(self):
        self.start_time = time_ns()
        self._clock_start = monotonic_ns()
        self._clock_finish = None

    def finish(self):
        self._clock_finish = monotonic_ns()

    @property
    def duration(self):
        _clock_finish = self._clock_finish if self._clock_finish is not None else monotonic_ns()
        return _clock_finish - self._clock_start

    #
    # events
    #
    def add_event(self, event):
        self.events.append(event)


class Target:
    """A target that ignores all telemetry"""

    def __init__(self, level=log.WARNING):
        self.level = level

    def accepts_log_level(self, level):
        return level <= self.level

    def start(self, trace_id=None, parent_id=None, id=None, name=None):
        return Span(trace_id, parent_id, id, name)

    def finish(self, tags, span):
        pass

    def event(self, name, tags, span=None):
        if span:
            event = Event(name, tags=tags)
            span.add_event(event)

    def log(self, level, message, tags, span=None):
        pass

    def error(self, message, exception, tags, span=None):
        pass

    def magnitude(self, name, value, tags, span=None):
        pass

    def count(self, name, value, tags, span=None):
        pass
