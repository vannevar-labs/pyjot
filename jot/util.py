import codecs
import inspect

_from_hex = codecs.getdecoder("hex")
_from_str = codecs.getencoder("ascii")
_to_hex = codecs.getencoder("hex")
_to_str = codecs.getdecoder("ascii")


def hex_encode(id):
    if id is None:
        return None
    hexbytes = _to_hex(id)[0]
    return _to_str(hexbytes)[0]


def hex_decode(id):
    if id is None:
        return None
    hexbytes = _from_str(id)[0]
    return _from_hex(hexbytes)[0]


def make_add_caller_tags(filename):
    def add_caller_tags(tags):
        frame = inspect.currentframe()

        # some versions of python do not give access to frames
        if frame is None:  # pragma: no cover
            return

        # this frame is for this function, so skip it
        frame = frame.f_back

        # now find the first frame that is not in indicated filename
        while frame:
            if frame.f_globals.get("__file__") != filename:
                break
            frame = frame.f_back

        # if we ran out of frames, just return
        if frame is None:
            return

        # add the caller tags
        tags["file"] = frame.f_globals.get("__file__")
        tags["line"] = frame.f_lineno
        tags["function"] = frame.f_code.co_name

    return add_caller_tags
