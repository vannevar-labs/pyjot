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

    @classmethod
    def _gen_id(cls):
        id = cls._next_id
        cls._next_id += 1
        return id

    def __init__(self, level=log.WARNING):
        self.level = level

    def _start(self, trace_id, parent_id, id, name):
        return Span(trace_id, parent_id, id, name)

    def accepts_log_level(self, level):
        return level <= self.level

    def start(self, parent=None, name=None):
        trace_id = parent.trace_id if parent is not None else self._gen_id()
        parent_id = parent.id if parent is not None else None
        id = self._gen_id()
        return self._start(trace_id, parent_id, id, name)

    def finish(self, span, tags):
        pass

    def event(self, span, name, tags):
        pass

    def log(self, span, level, message, tags):
        pass

    def error(self, span, message, exception, tags):
        pass

    def magnitude(self, span, name, value, tags):
        pass

    def count(self, span, name, value, tags):
        pass
