import codecs
import inspect
import os
import random

_from_hex = codecs.getdecoder("hex")
_from_str = codecs.getencoder("ascii")
_to_hex = codecs.getencoder("hex")
_to_str = codecs.getdecoder("ascii")


# Global variable to control deterministic behavior for testing
_test_random_seed = None


def _generate_id(num_bits):
    # For testing, use deterministic seed if set
    if _test_random_seed is not None:
        random.seed(_test_random_seed)
    
    id = random.getrandbits(num_bits)
    while id == 0:
        id = random.getrandbits(num_bits)
    return id


def set_test_random_seed(seed):
    """Set a deterministic seed for ID generation during testing."""
    global _test_random_seed
    _test_random_seed = seed


def clear_test_random_seed():
    """Clear the test seed to restore normal random behavior."""
    global _test_random_seed
    _test_random_seed = None


def _format_id(id, width):
    hex_str = hex(id)[2:]
    return hex_str.zfill(width)


def generate_trace_id():
    return _generate_id(128)


def generate_span_id():
    return _generate_id(64)


def format_trace_id(id):
    return _format_id(id, 32)


def format_span_id(id):
    return _format_id(id, 16)



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
