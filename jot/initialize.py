import importlib
import os
import platform
import sys

from . import facade, flush
from .base import Meter, Target
from .fanout import FanOutTarget
from .util import get_all_subclasses, get_env

TAG_PREFIX = "JOT_TAG_"
TAG_PREFIX_LEN = len(TAG_PREFIX)


def autoinit():
    if os.getenv("JOT_AUTOINIT", "true").lower() != "false":
        from .print import PrintTarget

        # ensure PrintTarget is registered, others can be registered with env vars
        PrintTarget()

        init_from_environment()


def init_from_environment():
    _import_modules_from_environment()
    target = _get_target_from_environment()
    tags = _get_tags_from_environment()
    init(target, **tags)


def init(target, /, **tags):
    facade.active_meter = Meter(target, None, **tags)
    flush.init()


def _import_modules_from_environment():
    modules = os.getenv("JOT_MODULES")
    if not modules:
        return
    for module in modules.split(","):
        try:
            importlib.import_module(module)
        except ImportError:
            pass


def _get_target_from_environment():
    targets = []
    for cls in get_all_subclasses(Target):
        env_target = cls.from_environment()
        if env_target is not None:
            targets.append(env_target)
    if not targets:
        target = Target()
    elif len(targets) == 1:
        target = targets[0]
    else:
        target = FanOutTarget(*targets)
    return target


def _get_tags_from_environment():
    tags = {}

    # standard UNIX environment variables
    _add_tag_from_env(tags, "HOSTNAME", "host.name")

    # custom JOT_TAG_ environment variables
    for key, val in os.environ.items():
        if key.startswith(TAG_PREFIX):
            tag_key = key[TAG_PREFIX_LEN:].lower().replace("_", ".")
            tags[tag_key] = val

    # python runtime information
    tags["process.runtime.name"] = sys.implementation.name
    tags["process.runtime.version"] = platform.python_version()
    tags["os.type"] = sys.platform
    tags["host.arch"] = platform.machine()

    return tags


def _add_tag_from_env(tags, env_var, tag_key):
    if val := get_env(env_var):
        tags[tag_key] = val


autoinit()
