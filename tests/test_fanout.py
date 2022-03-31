import pytest
from jot import log
from jot.base import Span, Target
from jot.fanout import FanOutTarget

TAGS_INDEX = -2
SPAN_INDEX = -1


@pytest.fixture
def fan():
    zero = Target(log.ERROR)
    one = Target(log.WARNING)
    return FanOutTarget(zero, one)


@pytest.fixture
def assert_forwards(fan, mocker):
    def _assert_forwards(method_name, *args):

        # create the mocks
        zero = mocker.spy(fan.targets[0], method_name)
        one = mocker.spy(fan.targets[1], method_name)

        # create the special args
        span = fan.start()
        tags = {"flooge": 91}

        # call the method
        func = getattr(fan, method_name)
        func(*args, tags, span)

        # assert the call was correct for zero
        zero.assert_called_once()
        assert zero.call_args.args[SPAN_INDEX] is span
        for i, a in enumerate(args):
            assert zero.call_args.args[i] == a
        assert zero.call_args.args[TAGS_INDEX] is not tags
        assert zero.call_args.args[TAGS_INDEX]["flooge"] == 91

        # assert the call was correct for one
        one.assert_called_once()
        assert one.call_args.args[SPAN_INDEX] is span
        for i, a in enumerate(args):
            assert one.call_args.args[i] == a
        assert one.call_args.args[TAGS_INDEX] is not tags
        assert one.call_args.args[TAGS_INDEX]["flooge"] == 91

    return _assert_forwards


def test_constructor():
    zero = Target()
    one = Target()
    fan = FanOutTarget(zero, one)

    assert zero in fan.targets
    assert one in fan.targets


def test_accepts_log_level(fan):
    assert fan.accepts_log_level(log.CRITICAL)
    assert fan.accepts_log_level(log.ERROR)
    assert fan.accepts_log_level(log.WARNING)
    assert not fan.accepts_log_level(log.INFO)
    assert not fan.accepts_log_level(log.DEBUG)
    assert not fan.accepts_log_level(log.ALL)


def test_finish(assert_forwards):
    assert_forwards("finish")


def test_event(assert_forwards):
    assert_forwards("event", "a test event")


def test_log(assert_forwards):
    assert_forwards("log", log.ERROR, "a log message")


def test_error(assert_forwards):
    try:
        4 / 0
    except ZeroDivisionError as e:
        assert_forwards("error", "error message", e)


def test_magnitude(assert_forwards):
    assert_forwards("magnitude", "metric name", 52)


def test_count(assert_forwards):
    assert_forwards("count", "metric name", 6)

def test_log_warning(fan, mocker):
    "Assert the fanout target honors log level when forwarding"

    # create the mocks
    zero = mocker.spy(fan.targets[0], "log")
    one = mocker.spy(fan.targets[1], "log")

    # create the special args
    span = fan.start()
    tags = {"flooge": 91}

    # call the method
    fan.log(log.WARNING, "a log message", tags, span)

    # assert the call was correct for zero
    zero.assert_not_called()

    # assert the call was correct for one
    one.assert_called_once()
    assert one.call_args.args[SPAN_INDEX] is span
    assert one.call_args.args[0] == log.WARNING
    assert one.call_args.args[1] == "a log message"
    assert one.call_args.args[TAGS_INDEX] is not tags
    assert one.call_args.args[TAGS_INDEX]["flooge"] == 91
