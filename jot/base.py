import codecs
import random
from contextlib import contextmanager
from time import monotonic_ns, time_ns

from . import log

_to_hex = codecs.getencoder("hex")
_to_str = codecs.getdecoder("ascii")


def _hex_encode(id):
    if id is None:
        return None
    hexbytes = _to_hex(id)[0]
    return _to_str(hexbytes)[0]


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

    def span(self, trace_id=None, parent_id=None, id=None, name=None):
        return Span(trace_id, parent_id, id, name)

    def start(self, parent=None, name=None):
        return Span.from_parent(parent, name)

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
