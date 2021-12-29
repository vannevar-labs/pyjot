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
        stderr.write(f"[{_now()}]")
        if type(tags) == dict:
            for k, v in tags.items():
                stderr.write(f" {k}={v}")
        else:
            stderr.write(f" {tags}")
        for c in chunks:
            stderr.write(f" {c}")
        stderr.write("\n")

    def finish(self, span, tags):
        tags["duration"] = span.duration
        self._write(span, tags, "finish", span.name)

    def event(self, span, name, tags):
        self.write(span, tags, name)

    def log(self, span, level, message, tags):
        if self.accepts_log_level(level):
            self._write(span, tags, log.name(level).upper(), message)

    def error(self, span, message, exception, tags):
        self._write(span, tags, "Error:", message)
        print_exception(exception)

    def magnitude(self, span, name, value, tags):
        self._write(span, tags, f"{name}={value}")

    def count(self, span, name, value, tags):
        self._write(span, tags, f"{name}={value}")
