import pytest
from io import StringIO

from jot import log
from jot.print import PrintTarget
from jot.base import Span

@pytest.fixture
def target():
    file = StringIO()
    return PrintTarget(log.WARNING, file)

@pytest.fixture
def span():
    span = Span(
        trace_id=b"\x12!]'E{2\xc9\xf5\x1b\x07\xb2\xb7H\xe7l",
        parent_id=b'rhX=\xb9\x96IG',
        id=b'\xe2\xd8\xcc\x0b[\xef\\\x8b',
        name="test-span"
    )
    return span

@pytest.fixture
def tags():
    return dict(plonk="lorp", wiff="nonk")

@pytest.fixture(autouse=True)
def monotonic(mocker):
    current_time = 0
    def monotonic_ns():
        nonlocal current_time
        current_time += 1000000 # 1M nanoseconds is a millisecond
        return current_time
    return mocker.patch('time.monotonic_ns', side_effect=monotonic_ns)



def test_accepts_log_level(target):
    assert target.accepts_log_level(log.CRITICAL)
    assert target.accepts_log_level(log.ERROR)
    assert target.accepts_log_level(log.WARNING)
    assert not target.accepts_log_level(log.INFO)
    assert not target.accepts_log_level(log.DEBUG)
    assert not target.accepts_log_level(log.ALL)

def test_start(target, span):
    target.start(span.trace_id, span.parent_id, span.id, span.name)
    output = target._file.getvalue()
    assert output == "[e2d8cc0b5bef5c8b/1] start test-span\n"

def test_finish(target, span, tags):
    span.duration = 432
    target.finish(tags, span)
    output = target._file.getvalue()
    assert output == "[e2d8cc0b5bef5c8b/1] plonk=lorp wiff=nonk duration=432 finish test-span\n"

def test_event(target, span, tags):
    target.event("test-event", tags, span)
    output = target._file.getvalue()
    assert output == "[e2d8cc0b5bef5c8b/1] plonk=lorp wiff=nonk test-event\n"

def test_log(target, span, tags):
    target.log(log.WARNING, "test-log-message", tags, span)
    output = target._file.getvalue()
    assert output == "[e2d8cc0b5bef5c8b/1] plonk=lorp wiff=nonk WARNING test-log-message\n"

def test_error(target, span, tags):
    try:
        1/0
    except ZeroDivisionError as err:
        target.error("got-error", err, tags, span)
    output = target._file.getvalue()
    assert output == "[e2d8cc0b5bef5c8b/1] plonk=lorp wiff=nonk Error: got-error\n"

def test_magnitude(target, span, tags):
    target.magnitude("test-magnitude", 32, tags, span)
    output = target._file.getvalue()
    assert output == "[e2d8cc0b5bef5c8b/1] plonk=lorp wiff=nonk test-magnitude=32\n"

def test_magnitude(target, span, tags):
    target.magnitude("test-count", 25, tags, span)
    output = target._file.getvalue()
    assert output == "[e2d8cc0b5bef5c8b/1] plonk=lorp wiff=nonk test-count=25\n"
