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
            method(target, *rest, tags, span)

    return wrapped


class FanOutTarget(Target):
    """A target that forwards calls to multiple targets"""

    def __init__(self, *targets):
        self.targets = targets

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
