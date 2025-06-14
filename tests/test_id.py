from jot.util import format_span_id, format_trace_id, generate_span_id, generate_trace_id


def test_generate_trace_id():
    id = generate_trace_id()
    assert isinstance(id, bytes)
    assert len(id) == 16


def test_generate_span_id():
    id = generate_span_id()
    assert isinstance(id, bytes)
    assert len(id) == 8


def test_format_trace_id():
    id = generate_trace_id()
    formatted = format_trace_id(id)
    assert isinstance(formatted, str)
    assert len(formatted) == 32


def test_format_span_id():
    id = generate_span_id()
    formatted = format_span_id(id)
    assert isinstance(formatted, str)
    assert len(formatted) == 16
