import sys

from .util import get_env

# define log levels
NOTHING = 0
CRITICAL = 10
ERROR = 20
WARNING = 30
INFO = 40
DEBUG = 50
ALL = 100

# set the default log level based on the environment variable LOG_LEVEL, or WARNING if not set
DEFAULT = getattr(sys.modules[__name__], get_env("LOG_LEVEL", "WARNING").upper())


def name(level):
    if level == NOTHING:
        return "nothing"
    elif level == CRITICAL:
        return "critical"
    elif level == ERROR:
        return "error"
    elif level == WARNING:
        return "warning"
    elif level == INFO:
        return "info"
    elif level == DEBUG:
        return "debug"
    elif level == ALL:
        return "all"
