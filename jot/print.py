import sys
import time
import traceback

from . import log
from .base import Target
from .util import hex_encode_bytes


def _now():
    return time.monotonic_ns() // 1000000


class PrintTarget(Target):
    """A target the prints telemetry to stderr"""

    def __init__(self, level=log.DEFAULT, file=sys.stderr):
        super().__init__(level)
        self._file = file

    def format_trace_id(self, trace_id):
        if not isinstance(trace_id, bytes):
            return str(trace_id)
        return super().format_trace_id(trace_id)

    def format_span_id(self, span_id):
        if not isinstance(span_id, bytes):
            return str(span_id)
        return super().format_span_id(span_id)

    def start(self, trace_id=None, parent_id=None, id=None, name=None):
        span = super().start(trace_id, parent_id, id, name)
        self._write(span, {}, "start", name)
        return span

    def finish(self, tags, span):
        tags["duration"] = span.duration
        self._write(span, tags, "finish", span.name)

    def event(self, name, tags, span=None):
        self._write(span, tags, name)

    def log(self, level, message, tags, span=None):
        if self.accepts_log_level(level):
            self._write(span, tags, log.name(level).upper(), message)

    def error(self, message, exception, tags, span=None):
        self._write(span, tags, "Error:", message)
        lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
        print("".join(lines), file=self._file)

    def magnitude(self, name, value, tags, span=None):
        self._write(span, tags, f"{name}={value}")

    def count(self, name, value, tags, span=None):
        self._write(span, tags, f"{name}={value}")

    def _write(self, span, tags=None, *more):
        mns = _now()
        span_id = self.format_span_id(span.id) if span else ""
        chunks = [f"[{span_id}/{mns}]"]
        if isinstance(tags, dict):
            for k, v in tags.items():
                if isinstance(v, bytes):
                    v = hex_encode_bytes(v)
                chunks.append(f"{k}={v}")
        else:
            chunks.append(tags)
        chunks.extend(more)
        print(*chunks, file=self._file)
