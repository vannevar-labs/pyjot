from jot.base import Span

HEX_ALPHABET = "0123456789abcdef"

def assert_is_hex(value):
    assert isinstance(value, str)
    for c in value:
        assert c in HEX_ALPHABET

def test_constructor_defaults():
    span = Span()
    assert isinstance(span.trace_id, bytes)
    assert span.parent_id is None
    assert isinstance(span.id, bytes)
    assert span.name is None


def test_constructor_keywords():
    trace_id = Span.gen_trace_id()
    parent_id = Span.gen_span_id()
    id = Span.gen_span_id()
    name = "the name of the span"

    span = Span(trace_id=trace_id, parent_id=parent_id, id=id, name=name)
    assert span.trace_id == trace_id
    assert span.parent_id == parent_id
    assert span.id == id
    assert span.name == name


def test_trace_id():
    trace_id = Span.gen_trace_id()
    assert isinstance(trace_id, bytes)
    assert len(trace_id) == 16


def test_span_id():
    span_id = Span.gen_span_id()
    assert isinstance(span_id, bytes)
    assert len(span_id) == 8


def test_trace_id_hex():
    value = Span().trace_id_hex
    assert_is_hex(value)
    assert len(value) == 32

def test_parent_id_hex():
    value = Span(parent_id=Span.gen_span_id()).parent_id_hex
    assert_is_hex(value)
    assert len(value) == 16

def test_id_hex():
    value = Span().id_hex
    assert_is_hex(value)
    assert len(value) == 16
