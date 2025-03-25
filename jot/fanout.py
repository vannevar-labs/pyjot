import sys
from copy import copy

from .base import Target


def _forward(method):
    def wrapped(self, *args):
        # Targets are expecting to be able to modify tags dictionaries without causing problems, so
        # we have to make a copy of the dictionary before making the call. Tags is the penultimate
        # argument to all methods, so this is straightforward.
        rest = args[:-2]
        span = args[-1]
        for target in self.targets:
            tags = copy(args[-2])
            try:
                method(target, *rest, tags, span)
            except Exception as e:
                print(f"Error forwarding to {target}: {e}", file=sys.stderr)

    return wrapped


class FanOutTarget(Target):
    """A target that forwards calls to multiple targets"""

    @classmethod
    def default(cls, level=None):
        target = Target.default(level)
        return cls(target, level=level)

    def __init__(self, *targets, level=None):
        self.targets = targets

    def generate_trace_id(self):
        if not self.targets:
            return super().generate_trace_id()
        return self.targets[0].generate_trace_id()

    def generate_span_id(self):
        if not self.targets:
            return super().generate_span_id()
        return self.targets[0].generate_span_id()

    def format_trace_id(self, trace_id):
        if not self.targets:
            return super().format_trace_id(trace_id)
        return self.targets[0].format_trace_id(trace_id)

    def format_span_id(self, span_id):
        if not self.targets:
            return super().format_span_id(span_id)
        return self.targets[0].format_span_id(span_id)

    def accepts_log_level(self, level):
        return any(t.accepts_log_level(level) for t in self.targets)

    @_forward
    def finish(target, tags, span):
        target.finish(tags, span)

    @_forward
    def event(target, name, tags, span=None):
        target.event(name, tags, span)

    @_forward
    def log(target, level, message, tags, span=None):
        if target.accepts_log_level(level):
            target.log(level, message, tags, span)

    @_forward
    def error(target, message, exception, tags, span=None):
        target.error(message, exception, tags, span)

    @_forward
    def magnitude(target, name, value, tags, span=None):
        target.magnitude(name, value, tags, span)

    @_forward
    def count(target, name, value, tags, span=None):
        target.count(name, value, tags, span)
