from copy import copy


class FanOutSpan:
    "A span that forwards calls to multiple spans"

    def __init__(self, spans):
        self.spans = spans

    def start(self):
        for s in self.spans:
            s.start()

    def finish(self):
        for s in self.spans:
            s.finish()

    @property
    def duration(self):
        return sum(s.duration for s in self.spans) / len(self.spans)


class FanOutTarget:
    """A target that forwards calls to multiple targets"""

    def __init__(self, *targets):
        self.targets = targets

    def _exec(self, method_name, span, *args):
        "Call the named method on each target with the correct span and forward other arguments"

        # Targets are expecting to be able to modify tags dictionaries without causing problems, so 
        # we have to make a copy of the dictionary before making the call. Tags is the last argument
        # to all methods, so this is straightforward.
        last = len(args) - 1
        middle = args[:-1]
        for target, sp in zip(self.targets, span.spans):
            tags = copy(args[last])
            func = getattr(target, method_name)
            func(sp, *middle, tags)

    def accepts_log_level(self, level):
        return any(t.accepts_log_level(level) for t in self.targets)

    def start(self, parent=None, name=None):
        spans = parent.spans if parent is not None else [None for t in self.targets]
        children = [t.start(p, name) for t, p in zip(self.targets, spans)]
        return FanOutSpan(children)

    def finish(self, span, tags):
        self._exec("finish", span, tags)

    def event(self, span, name, tags):
        self._exec("event", span, name, tags)

    def log(self, span, level, message, tags):
        self._exec("log", span, level, message, tags)

    def error(self, span, message, exception, tags):
        self._exec("error", span, message, exception, tags)

    def magnitude(self, span, name, value, tags):
        self._exec("magnitude", span, name, value, tags)

    def count(self, span, name, value, tags):
        self._exec("count", span, name, value, tags)
