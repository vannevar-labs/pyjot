from pkgutil import extend_path

from . import decorators, facade, initialize, logger, util

__path__ = extend_path(__path__, __name__)
del extend_path


# re-export init functions
init = initialize.init
init_from_environment = initialize.init_from_environment

# re-export util functions
generate_trace_id = util.generate_trace_id
generate_span_id = util.generate_span_id

# re-export facade functions
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
