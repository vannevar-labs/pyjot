from contextlib import contextmanager

from . import log
from .base import Target


class Telemeter:
    """The instrumentation interface"""

    def __init__(self, target=None, span=None, dtags={}, **kwtags) -> None:
        self.target = target if target is not None else Target()
        self.span = span
        self.tags = {**dtags, **kwtags}

    """Tracing Methods"""

    def start(self, name, dtags={}, **kwtags):
        tags = {**self.tags, **dtags, **kwtags}
        span = self.target.start(self.span, name)
        return Telemeter(self.target, span, **tags)

    def finish(self, dtags={}, **kwtags):
        tags = {**self.tags, **dtags, **kwtags}
        self.span.finish()
        self.target.finish(tags, self.span)

    def event(self, name, dtags={}, **kwtags):
        tags = {**self.tags, **dtags, **kwtags}
        self.target.event(name, tags, self.span)

    """Logging methods"""

    def debug(self, message, dtags={}, **kwtags):
        if self.target.accepts_log_level(log.DEBUG):
            tags = {**self.tags, **dtags, **kwtags}
            self.target.log(log.DEBUG, message, tags, self.span)

    def info(self, message, dtags={}, **kwtags):
        if self.target.accepts_log_level(log.INFO):
            tags = {**self.tags, **dtags, **kwtags}
            self.target.log(log.INFO, message, tags, self.span)

    def warning(self, message, dtags={}, **kwtags):
        if self.target.accepts_log_level(log.WARNING):
            tags = {**self.tags, **dtags, **kwtags}
            self.target.log(log.WARNING, message, tags, self.span)

    """Error methods"""

    def error(self, message, exception, dtags={}, **kwtags):
        tags = {**self.tags, **dtags, **kwtags}
        self.target.error(message, exception, tags, self.span)

    """Metrics methods"""

    def magnitude(self, name, value, dtags={}, **kwtags):
        # TODO: check that value is a number
        tags = {**self.tags, **dtags, **kwtags}
        self.target.magnitude(name, value, tags, self.span)

    def count(self, name, value, dtags={}, **kwtags):
        # TODO: check that value is an integer
        tags = {**self.tags, **dtags, **kwtags}
        self.target.count(name, value, tags, self.span)
