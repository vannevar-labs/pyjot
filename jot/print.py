import datetime
from sys import stderr
from time import time
from traceback import print_exception
from time import monotonic_ns, time_ns

from . import log
from .base import Target

def _now():
    return monotonic_ns() // 1000000


class PrintTarget(Target):
    """A target the prints telemetry to stderr"""

    @staticmethod
    def _write(span, tags=None, *chunks):
        stderr.write(f"[{span.id_hex}/{_now()}] ")
        if isinstance(tags, dict):
            for k, v in tags.items():
                stderr.write(f" {k}={v}")
        else:
            stderr.write(f" {tags}")
        for c in chunks:
            stderr.write(f" {c}")
        stderr.write("\n")

    def start(self, parent=None, name=None):
        span = super().start(parent, name)
        self._write(span, {}, "start", name)
        return span

    def finish(self, tags, span):
        tags["duration"] = span.duration
        self._write(span, tags, "finish", span.name)

    def event(self, name, tags, span=None):
        self.write(span, tags, name)

    def log(self, level, message, tags, span=None):
        if self.accepts_log_level(level):
            self._write(span, tags, log.name(level).upper(), message)

    def error(self, message, exception, tags, span=None):
        self._write(span, tags, "Error:", message)
        print(exception)

    def magnitude(self, name, value, tags, span=None):
        self._write(span, tags, f"{name}={value}")

    def count(self, name, value, tags, span=None):
        self._write(span, tags, f"{name}={value}")
