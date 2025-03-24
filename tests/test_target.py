from jot import log
from jot.base import Target


def test_default_constructor():
    target = Target()
    assert target.level == log.DEFAULT


def test_explicit_constructor():
    target = Target(log.INFO)
    assert target.level == log.INFO


def test_trace_id():
    target = Target()
    trace_id = target.generate_trace_id()
    assert isinstance(trace_id, bytes)
    assert len(trace_id) == 16


def test_span_id():
    target = Target()
    span_id = target.generate_span_id()
    assert isinstance(span_id, bytes)
    assert len(span_id) == 8
