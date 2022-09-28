from jot.util import hex_encode, hex_decode

def test_from_hex():
    actual = hex_decode("be71ef7f12c881e0fa9c01396a4a47db")
    expected = b"\xbeq\xef\x7f\x12\xc8\x81\xe0\xfa\x9c\x019jJG\xdb"
    assert actual == expected


def test_from_hex_none():
    actual = hex_decode(None)
    assert actual is None


def test_to_hex():
    actual = hex_encode(b"\xbeq\xef\x7f\x12\xc8\x81\xe0\xfa\x9c\x019jJG\xdb")
    expected = "be71ef7f12c881e0fa9c01396a4a47db"
    assert actual == expected

def test_to_hex_none():
    actual = hex_encode(None)
    assert actual is None
