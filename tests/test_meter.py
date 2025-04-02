import inspect

import pytest
from callee.numbers import Integer

from jot import log, util
from jot.base import Meter, Span, Target

EXPECTED_TAGS = {"plonk": 42}


def tags(**tags):
    return {**EXPECTED_TAGS, **tags}


def logtags(**tags):
    frame = inspect.currentframe()
    frame = frame.f_back
    return {
        **EXPECTED_TAGS,
        **tags,
        "file": __file__,
        "line": Integer(),
        "function": frame.f_code.co_name,
    }


@pytest.fixture
def target():
    return Target(log.ALL)


@pytest.fixture(params=["with_span", "without_span"])
def jot(request, target):
    span = Span() if request.param == "with_span" else None
    return Meter(target, span, plonk=42)


def test_start(jot, target):
    child = jot.start("subtask")
    assert len(jot.tags) == 1
    assert child.target is target
    assert child.active_span is not jot.active_span


def test_start_tags(jot, target, tags, assert_tags_are_correct):
    child = jot.start("subtask", **tags)
    assert len(jot.tags) == 1
    assert child.target is target
    assert child.active_span is not jot.active_span
    assert_tags_are_correct(child)


def test_start_trace_id(jot, target):
    trace_id = util.generate_trace_id()
    span_id = util.generate_span_id()
    child = jot.start("child", trace_id=trace_id)
    assert child.active_span.trace_id == trace_id
    assert child.active_span.parent_id is None
    assert isinstance(child.active_span.id, type(span_id))
    assert child.active_span.name == "child"


def test_start_parent_id(jot, target):
    trace_id = util.generate_trace_id()
    parent_id = util.generate_span_id()
    child = jot.start("child", trace_id=trace_id, parent_id=parent_id)
    assert child.active_span.trace_id == trace_id
    assert child.active_span.parent_id is parent_id
    assert isinstance(child.active_span.id, type(parent_id))
    assert child.active_span.name == "child"


def test_start_name_tag(jot):
    child = jot.start("child", name="floopy")
    assert child.tags["name"] == "floopy"


def test_start_no_positional_trace_id(jot):
    with pytest.raises(TypeError):
        jot.start("child", "positional-trace-id")


def test_event(jot, target, mocker):
    spy = mocker.spy(target, "event")
    jot.event("test-event")
    spy.assert_called_once_with("test-event", EXPECTED_TAGS, jot.active_span)


def test_event_tags(jot, target, mocker, tags, child_tags):
    spy = mocker.spy(target, "event")
    jot.event("test-event", **tags)
    spy.assert_called_once_with("test-event", child_tags, jot.active_span)


def test_event_name_tag(jot, target, mocker):
    tspy = mocker.spy(target, "event")
    jot.event("test-event", name="gronk")
    tspy.assert_called_once_with("test-event", tags(name="gronk"), jot.active_span)


def test_debug(jot, target, mocker):
    spy = mocker.spy(target, "log")
    jot.debug("test log message")
    spy.assert_called_once_with(log.DEBUG, "test log message", logtags(), jot.active_span)


def test_debug_tags(jot, target, mocker, tags, child_tags):
    spy = mocker.spy(target, "log")
    jot.debug("test log message", **tags)
    expected_tags = {**child_tags, **logtags()}
    spy.assert_called_once_with(log.DEBUG, "test log message", expected_tags, jot.active_span)


def test_debug_message_tag(jot, mocker):
    tspy = mocker.spy(jot.target, "log")
    jot.debug("test log message", message="gronk")
    tspy.assert_called_once_with(
        log.DEBUG, "test log message", logtags(message="gronk"), jot.active_span
    )


def test_info(jot, target, mocker):
    spy = mocker.spy(target, "log")
    jot.info("test log message")
    spy.assert_called_once_with(log.INFO, "test log message", logtags(), jot.active_span)


def test_info_tags(jot, target, mocker, tags, child_tags):
    spy = mocker.spy(target, "log")
    jot.info("test log message", **tags)
    expected_tags = {**child_tags, **logtags()}
    spy.assert_called_once_with(log.INFO, "test log message", expected_tags, jot.active_span)


def test_info_message_tag(jot, target, mocker):
    tspy = mocker.spy(target, "log")
    jot.info("test log message", message="gronk")
    tspy.assert_called_once_with(
        log.INFO, "test log message", logtags(message="gronk"), jot.active_span
    )


def test_warning(jot, target, mocker):
    spy = mocker.spy(target, "log")
    jot.warning("test log message")
    spy.assert_called_once_with(log.WARNING, "test log message", logtags(), jot.active_span)


def test_warning_tags(jot, target, mocker, tags, child_tags):
    spy = mocker.spy(target, "log")
    jot.warning("test log message", **tags)
    expected_tags = {**child_tags, **logtags()}
    spy.assert_called_once_with(log.WARNING, "test log message", expected_tags, jot.active_span)


def test_warning_message_tag(jot, target, mocker):
    tspy = mocker.spy(target, "log")
    jot.warning("test log message", message="gronk")
    tspy.assert_called_once_with(
        log.WARNING, "test log message", logtags(message="gronk"), jot.active_span
    )


def test_ignored_debug(mocker, target):
    target.level = log.NOTHING
    jot = Meter(target)
    spy = mocker.spy(jot.target, "log")
    jot.debug("test log message")
    spy.assert_not_called()


def test_ignored_info(mocker, target):
    target.level = log.NOTHING
    jot = Meter(target)
    spy = mocker.spy(jot.target, "log")
    jot.info("test log message")
    spy.assert_not_called()


def test_ignored_warning(mocker, target):
    target.level = log.NOTHING
    jot = Meter(target)
    spy = mocker.spy(jot.target, "log")
    jot.warning("test log message")
    spy.assert_not_called()


def test_error(jot, target, mocker):
    spy = mocker.spy(target, "error")
    try:
        4 / 0
    except ZeroDivisionError as e:
        jot.error("caught test error", e)
        spy.assert_called_once_with("caught test error", e, EXPECTED_TAGS, jot.active_span)


def test_error_tags(jot, target, mocker, tags, child_tags):
    spy = mocker.spy(target, "error")
    try:
        4 / 0
    except ZeroDivisionError as e:
        jot.error("caught test error", e, **tags)
        spy.assert_called_once_with("caught test error", e, child_tags, jot.active_span)


def test_error_message_tag(jot, target, mocker):
    spy = mocker.spy(target, "error")
    try:
        4 / 0
    except ZeroDivisionError as e:
        jot.error("caught test error", e, message="zork")
        expected_tags = {**EXPECTED_TAGS, "message": "zork"}
        spy.assert_called_once_with("caught test error", e, expected_tags, jot.active_span)


def test_error_exception_tag(jot, target, mocker):
    spy = mocker.spy(target, "error")
    try:
        4 / 0
    except ZeroDivisionError as e:
        jot.error("caught test error", e, exception="zork")
        expected_tags = {**EXPECTED_TAGS, "exception": "zork"}
        spy.assert_called_once_with("caught test error", e, expected_tags, jot.active_span)


def test_magnitude(jot, target, mocker):
    spy = mocker.spy(target, "magnitude")
    jot.magnitude("zishy", 105)
    spy.assert_called_once_with("zishy", 105, EXPECTED_TAGS, jot.active_span)


def test_magnitude_tags(jot, target, mocker, tags, child_tags):
    spy = mocker.spy(target, "magnitude")
    jot.magnitude("zishy", 105, **tags)
    spy.assert_called_once_with("zishy", 105, child_tags, jot.active_span)


def test_magnitude_name_tag(jot, target, mocker):
    spy = mocker.spy(target, "magnitude")
    jot.magnitude("zishy", 105, name="worg")
    spy.assert_called_once_with("zishy", 105, tags(name="worg"), jot.active_span)


def test_magnitude_value_tag(jot, mocker):
    spy = mocker.spy(jot.target, "magnitude")
    jot.magnitude("zishy", 105, value="worg")
    spy.assert_called_once_with("zishy", 105, tags(value="worg"), jot.active_span)


def test_count(jot, target, mocker):
    spy = mocker.spy(target, "count")
    jot.count("zishy", 105)
    spy.assert_called_once_with("zishy", 105, EXPECTED_TAGS, jot.active_span)


def test_count_tags(jot, target, mocker, tags, child_tags):
    spy = mocker.spy(target, "count")
    jot.count("zishy", 105, **tags)
    spy.assert_called_once_with("zishy", 105, child_tags, jot.active_span)


def test_count_name_tag(jot, target, mocker):
    spy = mocker.spy(target, "count")
    jot.count("zishy", 105, name="worg")
    spy.assert_called_once_with("zishy", 105, tags(name="worg"), jot.active_span)


def test_count_value_tag(jot, target, mocker):
    spy = mocker.spy(target, "count")
    jot.count("zishy", 105, value="worg")
    spy.assert_called_once_with("zishy", 105, tags(value="worg"), jot.active_span)
