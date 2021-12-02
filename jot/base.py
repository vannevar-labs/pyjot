from time import time_ns, monotonic_ns


class Span:
    """A span that tracks duration"""

    def __init__(self, trace_id, parent_id, id, name=None):
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.id = id
        self.name = name if name is not None else f"span-{self.id}"
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

    def start(self, parent=None, name=None):
        trace_id = parent.trace_id if parent is not None else self._gen_id()
        parent_id = parent.id if parent is not None else self._gen_id()
        id = self._gen_id()
        name = name if name is not None else f"span-{id}"
        return Span(trace_id, parent_id, id, name)

    def finish(self, span, tags):
        pass

    def log(self, span, level, message, tags):
        pass

    def error(self, span, message, exception, tags):
        pass

    def magnitude(self, span, name, value, tags):
        pass

    def count(self, span, name, value, tags):
        pass
