import pytest
from jot import log
from jot.base import Target
from jot.fanout import FanOutTarget


@pytest.fixture
def twelve():
    zero = Target(log.ERROR)
    one = Target(log.WARNING)
    return FanOutTarget(zero, one)


def test_constructor():
    zero = Target()
    one = Target()
    fan = FanOutTarget(zero, one)

    assert zero in fan.targets
    assert one in fan.targets


def test_accepts_log_level(twelve):
    assert twelve.accepts_log_level(log.CRITICAL)
    assert twelve.accepts_log_level(log.ERROR)
    assert twelve.accepts_log_level(log.WARNING)
    assert not twelve.accepts_log_level(log.INFO)
    assert not twelve.accepts_log_level(log.DEBUG)
    assert not twelve.accepts_log_level(log.ALL)


def test_start_root(twelve):
    root = twelve.start()
    assert len(root.spans) == 2
    for s in root.spans:
        assert s.parent_id is None
        assert s.name is None
        assert s.start_time is not None
        assert s.duration is not None


def test_start_child(twelve):
    parent = twelve.start()
    child = twelve.start(parent)
    assert len(child.spans) == 2
    assert child.spans[0].parent_id == parent.spans[0].id
    assert child.spans[1].parent_id == parent.spans[1].id


def test_start_name(twelve):
    root = twelve.start(None, "root")
    assert root.spans[0].name == "root"
    assert root.spans[1].name == "root"


def run_test(twelve, mocker, method_name, *args):
    # create the mocks
    zero = mocker.spy(twelve.targets[0], method_name)
    one = mocker.spy(twelve.targets[1], method_name)

    # create the special args
    span = twelve.start()
    tags = {"flooge": 91}

    # call the method
    func = getattr(twelve, method_name)
    func(span, *args, tags)

    # assert the call was correct for zero
    tags_index = len(args) + 1
    zero.assert_called_once()
    assert zero.call_args.args[0] is span.spans[0]
    for i, a in enumerate(args):
        assert zero.call_args.args[i + 1] == a
    assert zero.call_args.args[tags_index] is not tags
    assert zero.call_args.args[tags_index]["flooge"] == 91

    # assert the call was correct for one
    one.assert_called_once()
    assert one.call_args.args[0] is span.spans[1]
    for i, a in enumerate(args):
        assert one.call_args.args[i + 1] == a
    assert one.call_args.args[tags_index] is not tags
    assert one.call_args.args[tags_index]["flooge"] == 91


def test_finish(twelve, mocker):
    run_test(twelve, mocker, "finish")


def test_event(twelve, mocker):
    run_test(twelve, mocker, "event", "a test event")


def test_log(twelve, mocker):
    run_test(twelve, mocker, "log", log.WARNING, "a log message")


def test_error(twelve, mocker):
    try:
        4 / 0
    except ZeroDivisionError as e:
        run_test(twelve, mocker, "error", "error message", e)


def test_magnitude(twelve, mocker):
    run_test(twelve, mocker, "magnitude", "metric name", 52)


def test_count(twelve, mocker):
    run_test(twelve, mocker, "count", "metric name", 6)
