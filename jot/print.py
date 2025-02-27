import sys
import time
import traceback

from . import log
from .base import Target


def _now():
    return time.monotonic_ns() // 1000000


class PrintTarget(Target):
    """A target the prints telemetry to stderr"""

    def __init__(self, level=log.DEFAULT, file=sys.stderr):
        super().__init__(level)
        self._file = file

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
        chunks = [f"[{span.id_hex}/{mns}]"]
        if isinstance(tags, dict):
            for k, v in tags.items():
                chunks.append(f"{k}={v}")
        else:
            chunks.append(tags)
        chunks.extend(more)
        print(*chunks, file=self._file)
