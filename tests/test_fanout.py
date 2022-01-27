import pytest
from jot import log
from jot.base import Target
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
        assert zero.call_args.args[SPAN_INDEX] is span.spans[0]
        for i, a in enumerate(args):
            assert zero.call_args.args[i] == a
        assert zero.call_args.args[TAGS_INDEX] is not tags
        assert zero.call_args.args[TAGS_INDEX]["flooge"] == 91

        # assert the call was correct for one
        one.assert_called_once()
        assert one.call_args.args[SPAN_INDEX] is span.spans[1]
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


def test_start_root(fan):
    root = fan.start()
    assert len(root.spans) == 2
    for s in root.spans:
        assert s.parent_id is None
        assert s.name is None
        assert s.start_time is not None
        assert s.duration is not None


def test_start_child(fan):
    parent = fan.start()
    child = fan.start(parent)
    assert len(child.spans) == 2
    assert child.spans[0].parent_id == parent.spans[0].id
    assert child.spans[1].parent_id == parent.spans[1].id


def test_start_name(fan):
    root = fan.start(None, "root")
    assert root.spans[0].name == "root"
    assert root.spans[1].name == "root"


def test_finish(assert_forwards):
    assert_forwards("finish")


def test_event(assert_forwards):
    assert_forwards("event", "a test event")


def test_log(assert_forwards):
    assert_forwards("log", log.WARNING, "a log message")


def test_error(assert_forwards):
    try:
        4 / 0
    except ZeroDivisionError as e:
        assert_forwards("error", "error message", e)


def test_magnitude(assert_forwards):
    assert_forwards("magnitude", "metric name", 52)


def test_count(assert_forwards):
    assert_forwards("count", "metric name", 6)
