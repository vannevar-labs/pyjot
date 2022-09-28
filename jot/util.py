import codecs

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
