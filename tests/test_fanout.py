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


def test_generate_trace_id():
    fan = FanOutTarget(IntTarget(), Target())
    fan_id = fan.generate_trace_id()
    assert fan_id == 1


def test_generate_span_id():
    fan = FanOutTarget(IntTarget(), Target())
    span_id = fan.generate_span_id()
    assert span_id == 2


def test_format_trace_id():
    fan = FanOutTarget(IntTarget(), Target())
    formatted = fan.format_trace_id(1)
    assert formatted == "1"


def test_format_span_id():
    fan = FanOutTarget(IntTarget(), Target())
    formatted = fan.format_span_id(2)
    assert formatted == "2"


def test_generate_trace_id_default():
    fan = FanOutTarget()
    fan_id = fan.generate_trace_id()
    assert fan_id is not None


def test_generate_span_id_default():
    fan = FanOutTarget()
    span_id = fan.generate_span_id()
    assert span_id is not None


def test_format_trace_id_default():
    fan = FanOutTarget()
    id = fan.generate_trace_id()
    formatted = fan.format_trace_id(id)
    assert isinstance(formatted, str)


def test_format_span_id_default():
    fan = FanOutTarget()
    id = fan.generate_span_id()
    formatted = fan.format_span_id(id)
    assert isinstance(formatted, str)


@pytest.fixture
def broken(mocker):
    broken = mocker.Mock()
    broken.side_effect = Exception("broken")
    for method_name in dir(Target):
        if not method_name.startswith("_"):
            method = getattr(broken, method_name)
            method.side_effect = Exception("broken")

    ok = mocker.MagicMock(spec=Target)

    return FanOutTarget(broken, ok)


@pytest.fixture
def ok(broken):
    return broken.targets[1]


def test_traps_errors_finish(broken, ok):
    span = ok.span()
    broken.finish({}, span)
    assert ok.finish.called


def test_traps_errors_event(broken, ok):
    broken.event("event", {})
    assert ok.event.called


def test_traps_errors_log(broken, ok):
    broken.log(log.INFO, "message", {})
    assert ok.log.called


def test_traps_errors_error(broken, ok):
    try:
        4 / 0
    except ZeroDivisionError as e:
        broken.error("message", e, {})
    assert ok.error.called


def test_traps_errors_magnitude(broken, ok):
    broken.magnitude("metric", 42, {})
    assert ok.magnitude.called


def test_traps_errors_count(broken, ok):
    broken.count("metric", 42, {})
    assert ok.count.called


class IntTarget:
    def generate_trace_id(self):
        return 1

    def generate_span_id(self):
        return 2

    def format_trace_id(self, trace_id):
        return str(trace_id)

    def format_span_id(self, span_id):
        return str(span_id)
