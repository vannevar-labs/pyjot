from . import base, decorators, facade, flush, logger

# allow extensions to the jot namespace
__path__ = __import__("pkgutil").extend_path(__path__, __name__)


def init(target, /, **tags):
    facade.active_meter = base.Meter(target, None, **tags)
    flush.init()


# re-export facade functions
generate_trace_id = facade.generate_trace_id
start = facade.start
finish = facade.finish
event = facade.event
debug = facade.debug
info = facade.info
warning = facade.warning
error = facade.error
magnitude = facade.magnitude
count = facade.count
span = facade.span

# re-export decorator functions
instrument = decorators.instrument

# re-export logger functions
handle_logs = logger.handle_logs
ignore_logs = logger.ignore_logs
