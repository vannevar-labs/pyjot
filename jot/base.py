from contextlib import contextmanager
from time import monotonic_ns, time_ns

from . import log


class Span:
    """A span that tracks duration"""

    def __init__(self, trace_id, parent_id, id, name=None):
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.id = id
        self.name = name
        self.start()

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


class Target:
    """A target that ignores all telemetry"""

    _next_id = 1
    _span_class = Span

    @classmethod
    def _gen_id(cls):
        id = cls._next_id
        cls._next_id += 1
        return id

    @classmethod
    def _gen_trace_id(cls):
        return cls._gen_id()

    @classmethod
    def _gen_span_id(cls):
        return cls._gen_id()

    def __init__(self, level=log.WARNING):
        self.level = level

    def accepts_log_level(self, level):
        return level <= self.level

    def span(self, trace_id=None, parent_id=None, id=None, name=None):
        trace_id = self._gen_id() if trace_id is None else trace_id
        id = self._gen_id() if id is None else id
        return self._span_class(trace_id, parent_id, id, name)

    def start(self, parent=None, name=None):
        trace_id = parent.trace_id if parent is not None else self._gen_id()
        parent_id = parent.id if parent is not None else None
        id = self._gen_id()
        return self.span(trace_id, parent_id, id, name)

    def finish(self, tags, span):
        pass

    def event(self, name, tags, span=None):
        pass

    def log(self, level, message, tags, span=None):
        pass

    def error(self, message, exception, tags, span=None):
        pass

    def magnitude(self, name, value, tags, span=None):
        pass

    def count(self, name, value, tags, span=None):
        pass
