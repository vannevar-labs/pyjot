import jot
from jot import TraceContext, facade, get_trace_context
from jot.util import generate_span_id, generate_trace_id


def test_create_with_positional_args():
    trace_id = generate_trace_id()
    span_id = generate_span_id()
    context = TraceContext(trace_id, span_id)

    assert context.trace_id == trace_id
    assert context.parent_id == span_id


def test_create_with_keyword_args():
    trace_id = generate_trace_id()
    span_id = generate_span_id()
    context = TraceContext(trace_id=trace_id, parent_id=span_id)
    assert context.trace_id == trace_id
    assert context.parent_id == span_id


def test_create_without_parent_id():
    trace_id = generate_trace_id()
    context = TraceContext(trace_id=trace_id)
    assert context.trace_id == trace_id
    assert context.parent_id is None


def test_create_default():
    context = TraceContext()
    assert type(context.trace_id) is bytes
    assert context.parent_id is None


def test_get_trace_context_no_active_span():
    context = get_trace_context()
    assert context is None


def test_get_trace_context_with_active_span():
    trace_id = generate_trace_id()
    with jot.span("test span", trace_id=trace_id) as m:
        old = facade._swap_active(m)
        context = get_trace_context()
        facade._swap_active(old)

    assert context is not None
    assert context.trace_id == trace_id
    assert context.parent_id == m.active_span.id
