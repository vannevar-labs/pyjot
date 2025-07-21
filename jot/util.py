import codecs
import inspect
import os
import random

_from_hex = codecs.getdecoder("hex")
_from_str = codecs.getencoder("ascii")
_to_hex = codecs.getencoder("hex")
_to_str = codecs.getdecoder("ascii")


# Global variable to control deterministic behavior for testing
_random = random.Random()

_invalid_span_id = b"\x00" * 16  # Invalid ID
_invalid_trace_id = b"\x00" * 32  # Invalid ID


def init_random(seed=None):
    global _random
    _random = random.Random(seed)


def _format_id(id, width):
    hex_str = hex(id)[2:]
    return hex_str.zfill(width)


def generate_trace_id():
    id = _random.randbytes(16)
    while id == _invalid_trace_id:
        id = _random.randbytes(16)
    return id


def generate_span_id():
    id = _random.randbytes(8)
    while id == _invalid_span_id:
        id = _random.randbytes(8)
    return id


def format_trace_id(id):
    return hex_encode_bytes(id)


def format_span_id(id):
    return hex_encode_bytes(id)


def hex_encode_bytes(id):
    if id is None:
        return None
    hexbytes = _to_hex(id)[0]
    return _to_str(hexbytes)[0]


def hex_decode_bytes(id):
    if id is None:
        return None
    hexbytes = _from_str(id)[0]
    return _from_hex(hexbytes)[0]


def add_caller_tags(tags):
    frame = inspect.currentframe()

    # some versions of python do not give access to frames
    if frame is None:  # pragma: no cover
        return

    # this frame is for this function, so skip it
    frame = frame.f_back

    # now find the first frame that is not in this package
    pdir = os.path.basename(os.path.dirname(__file__))
    while frame:
        fpath = frame.f_globals.get("__file__")
        if fpath is None:
            continue
        fdir = os.path.basename(os.path.dirname(fpath))
        if fdir != pdir:
            break
        frame = frame.f_back

    # if we ran out of frames, just return
    if frame is None:
        return

    # add the caller tags
    tags["file"] = frame.f_globals.get("__file__")
    tags["line"] = frame.f_lineno
    tags["function"] = frame.f_code.co_name


def get_env(name, default=None):
    varname = f"JOT_{name}"
    if varname in os.environ:
        return os.environ[varname]
    return os.environ.get(name, default)


def get_all_subclasses(cls):
    classes = set()
    add_subclasses(cls, classes)
    return classes


def add_subclasses(cls, classes):
    for subclass in cls.__subclasses__():
        classes.add(subclass)
        add_subclasses(subclass, classes)
