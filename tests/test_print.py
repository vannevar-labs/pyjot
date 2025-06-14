from io import StringIO

import pytest

from jot import log, util
from jot.base import Span
from jot.print import PrintTarget


@pytest.fixture
def target():
    file = StringIO()
    return PrintTarget(log.WARNING, file)


@pytest.fixture(params=[True, False], ids=["with_span", "without_span"])
def span(request):
    if request.param:
        span = Span(
            trace_id=util.generate_trace_id(),
            parent_id=util.generate_span_id(),
            id=util.generate_span_id(),
            name="test-span",
        )
        return span


@pytest.fixture
def span_id(span):
    if span:
        return util.format_span_id(span.id)
    return ""


@pytest.fixture
def tags():
    return dict(plonk="lorp", wiff="nonk")


@pytest.fixture(autouse=True)
def monotonic(mocker):
    current_time = 0

    def monotonic_ns():
        nonlocal current_time
        current_time += 1000000  # 1M nanoseconds is a millisecond
        return current_time

    return mocker.patch("time.monotonic_ns", side_effect=monotonic_ns)


def test_accepts_log_level(target):
    assert target.accepts_log_level(log.CRITICAL)
    assert target.accepts_log_level(log.ERROR)
    assert target.accepts_log_level(log.WARNING)
    assert not target.accepts_log_level(log.INFO)
    assert not target.accepts_log_level(log.DEBUG)
    assert not target.accepts_log_level(log.ALL)


def test_start_root(target):
    span_id = util.generate_span_id()
    span = Span(id=span_id, name="test-span")
    target.start({}, span)
    output = target._file.getvalue()
    assert output == f"[{util.format_span_id(span_id)}/1] start test-span\n"


def test_start_child(target):
    trace_id = util.generate_trace_id()
    parent_id = util.generate_span_id()
    span_id = util.generate_span_id()
    span = Span(trace_id=trace_id, parent_id=parent_id, id=span_id, name="test-span")
    target.start({}, span)
    output = target._file.getvalue()

    expected = f"[{util.format_span_id(span_id)}/1] start test-span\n"
    assert output == expected


def test_finish(target, span, span_id, tags):
    if span is None:
        return
    span.start()
    span.duration = 432
    target.finish(tags, span)
    output = target._file.getvalue()
    assert output == f"[{span_id}/1] plonk=lorp wiff=nonk duration=432 finish test-span\n"


def test_event(target, span, span_id, tags):
    target.event("test-event", tags, span)
    output = target._file.getvalue()
    assert output == f"[{span_id}/1] plonk=lorp wiff=nonk test-event\n"


def test_log(target, span, span_id, tags):
    target.log(log.WARNING, "test-log-message", tags, span)
    output = target._file.getvalue()
    assert output == f"[{span_id}/1] plonk=lorp wiff=nonk WARNING test-log-message\n"


def test_error(target, span, span_id, tags):
    try:
        return 1 / 0
    except ZeroDivisionError as err:
        target.error("got-error", err, tags, span)
    output = target._file.getvalue()
    assert output.startswith(f"[{span_id}/1] plonk=lorp wiff=nonk Error: got-error\n")
    assert "Traceback (most recent call last):" in output
    assert "ZeroDivisionError: division by zero" in output
    assert "test_print.py" in output
    assert "test_error" in output
    assert "1 / 0" in output


def test_magnitude(target, span, span_id, tags):
    target.magnitude("test-magnitude", 32, tags, span)
    output = target._file.getvalue()
    assert output == f"[{span_id}/1] plonk=lorp wiff=nonk test-magnitude=32\n"


def test_count(target, span, span_id, tags):
    target.count("test-count", 25, tags, span)
    output = target._file.getvalue()
    assert output == f"[{span_id}/1] plonk=lorp wiff=nonk test-count=25\n"


def test_log_bytes_tags(target):
    id = util.generate_span_id()
    idstr = util.format_span_id(id)
    target.log(log.WARNING, "test-log-message", {"id": id})
    output = target._file.getvalue()
    assert output == f"[/1] id={idstr} WARNING test-log-message\n"


def test_int_span_id(target):
    trace_id = util.generate_trace_id()
    span_id = util.generate_span_id()
    span_id_str = util.format_span_id(span_id)
    span = Span(trace_id=trace_id, id=span_id, name="test-span")
    target.log(log.WARNING, "test-log-message", {}, span)
    output = target._file.getvalue()
    assert output == f"[{span_id_str}/1] WARNING test-log-message\n"
