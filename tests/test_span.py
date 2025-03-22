from jot.base import Span, Target


def test_default_constructor():
    span = Span()
    assert span.trace_id is not None
    assert span.parent_id is None
    assert span.id is not None


def test_positional_constructor():
    trace_id = Target.generate_trace_id()
    parent_id = Target.generate_span_id()
    id = Target.generate_span_id()
    name = "the name of the span"

    span = Span(trace_id, parent_id, id, name)
    assert span.trace_id == trace_id
    assert span.parent_id == parent_id
    assert span.id == id
    assert span.name == name


def test_constructor_keywords():
    trace_id = Target.generate_trace_id()
    parent_id = Target.generate_span_id()
    id = Target.generate_span_id()
    name = "the name of the span"

    span = Span(trace_id=trace_id, parent_id=parent_id, id=id, name=name)
    assert span.trace_id == trace_id
    assert span.parent_id == parent_id
    assert span.id == id
    assert span.name == name
