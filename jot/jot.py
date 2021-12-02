from .base import Target


class Jot:
    """The instrumentation interface"""

    def __init__(self, target=None, span=None, *tagdicts) -> None:
        self.target = target if target is not None else Target()
        self.span = span if span is not None else self.target.start()
        self.tags = dict()
        for tags in tagdicts:
            self.tags.update(tags)

    def _merge(self, tagdicts):
        tags = self.tags.copy()
        for d in tagdicts:
            tags.update(d)
        return tags

    """Tracing Methods"""

    def start(self, name, *tagdicts):
        tags = self._merge(tagdicts)
        span = self.target.start(self.span, name)
        return Jot(self.target, span, tags)

    def finish(self, *tagdicts):
        self.span.finish()
        tags = self._merge(tagdicts)
        self.target.finish(self.span, tags)

    """Logging methods"""

    def debug(self, message, *tagdicts):
        tags = self._merge(tagdicts)
        self.target.log(self.span, "debug", message, tags)

    def info(self, message, *tagdicts):
        tags = self._merge(tagdicts)
        self.target.log(self.span, "info", message, tags)

    def warning(self, message, *tagdicts):
        tags = self._merge(tagdicts)
        self.target.log(self.span, "warning", message, tags)

    """Error methods"""

    def error(self, message, exception, *tagdicts):
        tags = self._merge(tagdicts)
        self.target.error(self.span, message, exception, tags)

    """Metrics methods"""

    def magnitude(self, name, value, *tagdicts):
        # TODO: check that value is a number
        tags = self._merge(tagdicts)
        self.target.magnitude(self.span, name, value, tags)

    def count(self, name, value, *tagdicts):
        # TODO: check that value is an integer
        tags = self._merge(tagdicts)
        self.target.count(self.span, name, value, tags)
