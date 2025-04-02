import logging

import jot
from jot import facade, log, util
from jot.base import Target

PY2JOT_MAP = {
    logging.CRITICAL: jot.log.CRITICAL,
    logging.ERROR: jot.log.ERROR,
    logging.WARNING: jot.log.WARNING,
    logging.INFO: jot.log.INFO,
    logging.DEBUG: jot.log.DEBUG,
    logging.NOTSET: jot.log.NOTHING,
}

JOT2PY_MAP = {v: k for k, v in PY2JOT_MAP.items()}

EXCLUDE = [
    "args",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "getMessage",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
]


def handle_logs(name=""):
    logger = logging.getLogger(name)
    if not any(isinstance(handler, JotLoggingHandler) for handler in logger.handlers):
        handler = JotLoggingHandler()
        logger.addHandler(handler)


def ignore_logs(name=""):
    logger = logging.getLogger(name)
    jot_handlers = [h for h in logger.handlers if isinstance(h, JotLoggingHandler)]
    for handler in jot_handlers:
        logger.removeHandler(handler)


class JotLoggingHandler(logging.Handler):
    def emit(self, record):
        # translate python logging level into jot level
        level = PY2JOT_MAP.get(record.levelno, jot.log.NOTHING)

        # basic tags
        tags = {
            "file": record.filename,
            "function": record.funcName,
            "line": record.lineno,
            "logger": record.name,
        }

        # It's a bit tricky to fish out the extra tags passed in the call the logger. They just
        # appear as attributes on the record object. We get all the attributes that don't start with
        # an underscore and aren't part of the standard record attributes.
        for attr in dir(record):
            if attr.startswith("_") or attr in EXCLUDE:
                continue
            tags[attr] = str(getattr(record, attr))

        target = facade.active_meter.target
        if target.accepts_log_level(level):
            target.log(level, record.getMessage(), tags, facade.active_meter.active_span)


class LoggerTarget(Target):
    """A target that logs telemetry to the python logging system"""

    def __init__(self, name="", level=log.DEFAULT):
        super().__init__(level)
        self.logger = logging.getLogger(name)

    def log(self, jot_level, message, tags, span=None):
        if span:
            tags.update(
                {
                    "trace_id": util.format_trace_id(span.trace_id),
                    "parent_id": util.format_span_id(span.parent_id),
                    "span_id": util.format_span_id(span.id),
                    "span_name": span.name,
                }
            )

        py_level = JOT2PY_MAP[jot_level]
        self.logger.log(py_level, message, extra=tags)
