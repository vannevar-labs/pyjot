from contextlib import contextmanager

from . import log
from .base import Target


class Telemeter:
    """The instrumentation interface"""

    def __init__(self, target=None, span=None, **tags) -> None:
        self.target = target if target is not None else Target()
        self.span = span
        self.tags = tags

    """Tracing Methods"""

    def start(self, name, **tags):
        tags = {**self.tags, **tags}
        span = self.target.start(self.span, name)
        return Telemeter(self.target, span, **tags)

    def finish(self, **tags):
        tags = {**self.tags, **tags}
        self.span.finish()
        self.target.finish(tags, self.span)

    def event(self, name, **tags):
        tags = {**self.tags, **tags}
        self.target.event(name, tags, self.span)

    """Logging methods"""

    def debug(self, message, **tags):
        if self.target.accepts_log_level(log.DEBUG):
            tags = {**self.tags, **tags}
            self.target.log(log.DEBUG, message, tags, self.span)

    def info(self, message, **tags):
        if self.target.accepts_log_level(log.INFO):
            tags = {**self.tags, **tags}
            self.target.log(log.INFO, message, tags, self.span)

    def warning(self, message, **tags):
        if self.target.accepts_log_level(log.WARNING):
            tags = {**self.tags, **tags}
            self.target.log(log.WARNING, message, tags, self.span)

    """Error methods"""

    def error(self, message, exception, **tags):
        tags = {**self.tags, **tags}
        self.target.error(message, exception, tags, self.span)

    """Metrics methods"""

    def magnitude(self, name, value, **tags):
        # TODO: check that value is a number
        tags = {**self.tags, **tags}
        self.target.magnitude(name, value, tags, self.span)

    def count(self, name, value, **tags):
        # TODO: check that value is an integer
        tags = {**self.tags, **tags}
        self.target.count(name, value, tags, self.span)
