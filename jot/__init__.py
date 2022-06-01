from . import facade
from . import flush
from . import decorators
from . import base

# allow extensions to the jot namespace
__path__ = __import__("pkgutil").extend_path(__path__, __name__)


# forward access of 'active' to the facade
def __getattr__(name):
    if name == "active":
        return facade.active
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __setattr__(name, value):
    if name == "active":
        facade.active = value
    else:
        globals()[name] = value


def init(target, dtags={}, **kwtags):
    facade.active = base.Telemeter(target, None, dtags, **kwtags)
    facade.stack = []
    flush.init()


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

# re-export generator functions
generator = decorators.generator
tag = decorators.tag
