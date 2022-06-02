import atexit
import sys

from . import facade as _facade

_flush_handlers = []


def init():
    # If an exception reaches the top of the stack without getting caught, this function will get called.
    # We want to report that exception, *unless* it's a KeyboardInterrupt (ie, the user pressed ^C).
    def report_uncaught_exception(exc_type, exc, exc_traceback):
        if not issubclass(exc_type, KeyboardInterrupt):
            _facade.active.error("Unhandled Exception", exc)
        old_hook(exc_type, exc, exc_traceback)

    # register the exception hook
    old_hook = sys.excepthook
    sys.excepthook = report_uncaught_exception

    # flush when shutting down python
    atexit.register(flush)


def add_handler(fn):
    _flush_handlers.append(fn)


def remove_handler(fn):
    _flush_handlers.remove(fn)


def remove_all_handlers():
    _flush_handlers.clear()


def flush():
    for fn in reversed(_flush_handlers):
        fn()
