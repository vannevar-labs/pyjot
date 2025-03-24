from time import monotonic_ns, time_ns

from . import log, util


class Meter:
    """The instrumentation interface"""

    def __init__(self, target=None, active_span=None, /, **tags) -> None:
        self.target = target if target is not None else Target()
        self.active_span = active_span
        self.tags = tags

    """Tracing Methods"""

    def span(self, name, /, *, trace_id=None, parent_id=None, **kwtags):
        tags = {**self.tags, **kwtags}
        if trace_id is not None:
            trace_id = trace_id
            parent_id = parent_id
        elif self.active_span is not None:
            trace_id = self.active_span.trace_id
            parent_id = self.active_span.id
        else:
            trace_id = None
            parent_id = None
        span = self.target.span(trace_id=trace_id, parent_id=parent_id, name=name)
        return Meter(self.target, span, **tags)

    def start(self, name=None, /, *, trace_id=None, parent_id=None, **kwtags):
        if name is not None:
            child = self.span(name, trace_id=trace_id, parent_id=parent_id, **kwtags)
            child.start()
            return child

        if self.active_span is None:
            raise RuntimeError("No active span to start")

        self.active_span.start()

    def finish(self, /, **kwtags):
        if self.active_span is None:
            raise RuntimeError("No active span to finish")
        if self.active_span.is_finished:
            raise RuntimeError("Span is already finished")

        tags = {**self.tags, **kwtags}
        self.active_span.finish()
        self.target.finish(tags, self.active_span)

    def event(self, name, /, **kwtags):
        tags = {**self.tags, **kwtags}
        self.target.event(name, tags, self.active_span)

    """Logging methods"""

    def debug(self, message, /, **kwtags):
        if self.target.accepts_log_level(log.DEBUG):
            tags = {**self.tags, **kwtags}
            util.add_caller_tags(tags)
            self.target.log(log.DEBUG, message, tags, self.active_span)

    def info(self, message, /, **kwtags):
        if self.target.accepts_log_level(log.INFO):
            tags = {**self.tags, **kwtags}
            util.add_caller_tags(tags)
            self.target.log(log.INFO, message, tags, self.active_span)

    def warning(self, message, /, **kwtags):
        if self.target.accepts_log_level(log.WARNING):
            tags = {**self.tags, **kwtags}
            util.add_caller_tags(tags)
            self.target.log(log.WARNING, message, tags, self.active_span)

    """Error methods"""

    def error(self, message, exception, /, **kwtags):
        tags = {**self.tags, **kwtags}
        self.target.error(message, exception, tags, self.active_span)

    """Metrics methods"""

    def magnitude(self, name, value, /, **kwtags):
        # TODO: check that value is a number
        tags = {**self.tags, **kwtags}
        self.target.magnitude(name, value, tags, self.active_span)

    def count(self, name, value, /, **kwtags):
        # TODO: check that value is an integer
        tags = {**self.tags, **kwtags}
        self.target.count(name, value, tags, self.active_span)

    """Context manager support"""

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            message = f"Error during {self.active_span.name}" if self.active_span else "Error"
            self.error(message, exc_value)
        self.finish()


class Event:
    def __init__(self, name, timestamp=None, tags={}):
        self.name = name
        self.timestamp = timestamp if timestamp else time_ns()
        self.tags = tags


class Span:
    @classmethod
    def from_parent(cls, parent, name=None):
        trace_id = parent.trace_id if parent else None
        parent_id = parent.id if parent else None
        return cls(trace_id, parent_id, name=name)

    def __init__(self, trace_id=None, parent_id=None, id=None, name=None):
        self.trace_id = trace_id if trace_id else util.generate_trace_id()
        self.parent_id = parent_id
        self.id = id if id else util.generate_span_id()
        self.name = name
        self.events = []
        self.baggage = {}
        self.start_time = None
        self._clock_start = None
        self._clock_finish = None

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
    def is_started(self):
        return self._clock_start is not None

    @property
    def is_finished(self):
        return self._clock_finish is not None

    @property
    def duration(self):
        _clock_finish = self._clock_finish if self._clock_finish is not None else monotonic_ns()
        return _clock_finish - self._clock_start

    @duration.setter
    def duration(self, ns):
        self._clock_finish = self._clock_start + ns

    @property
    def finish_time(self):
        return self.start_time + self.duration

    #
    # events
    #
    def add_event(self, event):
        self.events.append(event)


class Target:
    """A target that ignores all telemetry"""

    @classmethod
    def default(cls, level=None):
        return cls(level=level)

    def __init__(self, level=None):
        self.level = level if level is not None else log.DEFAULT

    def generate_trace_id(self):
        return util.generate_trace_id()

    def generate_span_id(self):
        return util.generate_span_id()

    def format_trace_id(self, trace_id):
        return util.format_trace_id(trace_id)

    def format_span_id(self, span_id):
        return util.format_span_id(span_id)

    def accepts_log_level(self, level):
        return level <= self.level

    def span(self, trace_id=None, parent_id=None, id=None, name=None):
        if trace_id is None:
            trace_id = self.generate_trace_id()
        if id is None:
            id = self.generate_span_id()
        return Span(trace_id, parent_id, id, name)

    def start(self, trace_id=None, parent_id=None, id=None, name=None):
        span = self.span(trace_id, parent_id, id, name)
        span.start()
        return span

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
