NOTHING = 0
CRITICAL = 10
ERROR = 20
WARNING = 30
INFO = 40
DEBUG = 50
ALL = 100


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
        return all
