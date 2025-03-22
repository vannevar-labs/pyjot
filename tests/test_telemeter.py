import inspect

import pytest
from callee.numbers import Integer

from jot import log
from jot.base import Span, Target, Telemeter
from jot.print import PrintTarget

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


@pytest.fixture(params=["with_span", "without_span"])
def jot(request):
    target = Target(log.ALL)
    span = target.start() if request.param == "with_span" else None
    return Telemeter(target, span, plonk=42)


def test_default_constructor():
    jot = Telemeter()
    assert isinstance(jot.target, Target)
    assert jot.span is None
    assert isinstance(jot.tags, dict)
    assert len(jot.tags) == 0


def test_default_constructor_tags(tags, assert_tags_are_correct):
    jot = Telemeter(None, None, **tags)
    assert isinstance(jot.target, Target)
    assert jot.span is None
    assert_tags_are_correct(jot)


def test_target_constructor():
    target = PrintTarget()
    jot = Telemeter(target)
    assert jot.target is target
    assert jot.span is None


def test_target_constructor_tags(tags, assert_tags_are_correct):
    target = PrintTarget()
    jot = Telemeter(target, None, **tags)
    assert jot.target is target
    assert jot.span is None
    assert_tags_are_correct(jot)


def test_span_constructor():
    span = Span(1, 2, 3)
    jot = Telemeter(None, span)
    assert isinstance(jot.target, Target)
    assert jot.span is span


def test_span_constructor_tags(tags, assert_tags_are_correct):
    span = Span(1, 2, 3)
    jot = Telemeter(None, span, **tags)
    assert isinstance(jot.target, Target)
    assert jot.span is span
    assert_tags_are_correct(jot)


def test_target_tag():
    jot = Telemeter(target="plict")
    assert jot.tags["target"] == "plict"


def test_span_tag():
    jot = Telemeter(span="plict")
    assert jot.tags["span"] == "plict"


def test_start(jot):
    child = jot.start("subtask")
    assert len(jot.tags) == 1
    assert child.target is jot.target
    assert child.span is not jot.span


def test_start_tags(jot, tags, assert_tags_are_correct):
    child = jot.start("subtask", **tags)
    assert len(jot.tags) == 1
    assert child.target is jot.target
    assert child.span is not jot.span
    assert_tags_are_correct(child)


def test_start_trace_id(jot):
    trace_id = Target.generate_trace_id()
    child = jot.start("child", trace_id=trace_id)
    assert child.span.trace_id == trace_id
    assert child.span.parent_id is None
    assert isinstance(child.span.id, bytes)
    assert child.span.name == "child"


def test_start_parent_id(jot):
    trace_id = Target.generate_trace_id()
    parent_id = Target.generate_span_id()
    child = jot.start("child", trace_id=trace_id, parent_id=parent_id)
    assert child.span.trace_id == trace_id
    assert child.span.parent_id is parent_id
    assert isinstance(child.span.id, bytes)
    assert child.span.name == "child"


def test_start_name_tag(jot):
    child = jot.start("child", name="floopy")
    assert child.tags["name"] == "floopy"


def test_start_no_positional_trace_id(jot):
    with pytest.raises(TypeError):
        jot.start("child", {}, "positional-trace-id")


def test_event(jot, mocker):
    spy = mocker.spy(jot.target, "event")
    jot.event("test-event")
    spy.assert_called_once_with("test-event", EXPECTED_TAGS, jot.span)


def test_event_tags(jot, mocker, tags, child_tags):
    spy = mocker.spy(jot.target, "event")
    jot.event("test-event", **tags)
    spy.assert_called_once_with("test-event", child_tags, jot.span)


def test_event_name_tag(jot, mocker):
    tspy = mocker.spy(jot.target, "event")
    jot.event("test-event", name="gronk")
    tspy.assert_called_once_with("test-event", tags(name="gronk"), jot.span)


def test_debug(jot, mocker):
    spy = mocker.spy(jot.target, "log")
    jot.debug("test log message")
    spy.assert_called_once_with(log.DEBUG, "test log message", logtags(), jot.span)


def test_debug_tags(jot, mocker, tags, child_tags):
    spy = mocker.spy(jot.target, "log")
    jot.debug("test log message", **tags)
    expected_tags = {**child_tags, **logtags()}
    spy.assert_called_once_with(log.DEBUG, "test log message", expected_tags, jot.span)


def test_debug_message_tag(jot, mocker):
    tspy = mocker.spy(jot.target, "log")
    jot.debug("test log message", message="gronk")
    tspy.assert_called_once_with(log.DEBUG, "test log message", logtags(message="gronk"), jot.span)


def test_info(jot, mocker):
    spy = mocker.spy(jot.target, "log")
    jot.info("test log message")
    spy.assert_called_once_with(log.INFO, "test log message", logtags(), jot.span)


def test_info_tags(jot, mocker, tags, child_tags):
    spy = mocker.spy(jot.target, "log")
    jot.info("test log message", **tags)
    expected_tags = {**child_tags, **logtags()}
    spy.assert_called_once_with(log.INFO, "test log message", expected_tags, jot.span)


def test_info_message_tag(jot, mocker):
    tspy = mocker.spy(jot.target, "log")
    jot.info("test log message", message="gronk")
    tspy.assert_called_once_with(log.INFO, "test log message", logtags(message="gronk"), jot.span)


def test_warning(jot, mocker):
    spy = mocker.spy(jot.target, "log")
    jot.warning("test log message")
    spy.assert_called_once_with(log.WARNING, "test log message", logtags(), jot.span)


def test_warning_tags(jot, mocker, tags, child_tags):
    spy = mocker.spy(jot.target, "log")
    jot.warning("test log message", **tags)
    expected_tags = {**child_tags, **logtags()}
    spy.assert_called_once_with(log.WARNING, "test log message", expected_tags, jot.span)


def test_warning_message_tag(jot, mocker):
    tspy = mocker.spy(jot.target, "log")
    jot.warning("test log message", message="gronk")
    tspy.assert_called_once_with(
        log.WARNING, "test log message", logtags(message="gronk"), jot.span
    )


def test_ignored_debug(mocker):
    target = Target(log.NOTHING)
    jot = Telemeter(target)
    spy = mocker.spy(jot.target, "log")
    jot.debug("test log message")
    spy.assert_not_called()


def test_ignored_info(mocker):
    target = Target(log.NOTHING)
    jot = Telemeter(target)
    spy = mocker.spy(jot.target, "log")
    jot.info("test log message")
    spy.assert_not_called()


def test_ignored_warning(mocker):
    target = Target(log.NOTHING)
    jot = Telemeter(target)
    spy = mocker.spy(jot.target, "log")
    jot.warning("test log message")
    spy.assert_not_called()


def test_error(jot, mocker):
    spy = mocker.spy(jot.target, "error")
    try:
        4 / 0
    except ZeroDivisionError as e:
        jot.error("caught test error", e)
        spy.assert_called_once_with("caught test error", e, EXPECTED_TAGS, jot.span)


def test_error_tags(jot, mocker, tags, child_tags):
    spy = mocker.spy(jot.target, "error")
    try:
        4 / 0
    except ZeroDivisionError as e:
        jot.error("caught test error", e, **tags)
        spy.assert_called_once_with("caught test error", e, child_tags, jot.span)


def test_error_message_tag(jot, mocker):
    spy = mocker.spy(jot.target, "error")
    try:
        4 / 0
    except ZeroDivisionError as e:
        jot.error("caught test error", e, message="zork")
        expected_tags = {**EXPECTED_TAGS, "message": "zork"}
        spy.assert_called_once_with("caught test error", e, expected_tags, jot.span)


def test_error_exception_tag(jot, mocker):
    spy = mocker.spy(jot.target, "error")
    try:
        4 / 0
    except ZeroDivisionError as e:
        jot.error("caught test error", e, exception="zork")
        expected_tags = {**EXPECTED_TAGS, "exception": "zork"}
        spy.assert_called_once_with("caught test error", e, expected_tags, jot.span)


def test_magnitude(jot, mocker):
    spy = mocker.spy(jot.target, "magnitude")
    jot.magnitude("zishy", 105)
    spy.assert_called_once_with("zishy", 105, EXPECTED_TAGS, jot.span)


def test_magnitude_tags(jot, mocker, tags, child_tags):
    spy = mocker.spy(jot.target, "magnitude")
    jot.magnitude("zishy", 105, **tags)
    spy.assert_called_once_with("zishy", 105, child_tags, jot.span)


def test_magnitude_name_tag(jot, mocker):
    spy = mocker.spy(jot.target, "magnitude")
    jot.magnitude("zishy", 105, name="worg")
    spy.assert_called_once_with("zishy", 105, tags(name="worg"), jot.span)


def test_magnitude_value_tag(jot, mocker):
    spy = mocker.spy(jot.target, "magnitude")
    jot.magnitude("zishy", 105, value="worg")
    spy.assert_called_once_with("zishy", 105, tags(value="worg"), jot.span)


def test_count(jot, mocker):
    spy = mocker.spy(jot.target, "count")
    jot.count("zishy", 105)
    spy.assert_called_once_with("zishy", 105, EXPECTED_TAGS, jot.span)


def test_count_tags(jot, mocker, tags, child_tags):
    spy = mocker.spy(jot.target, "count")
    jot.count("zishy", 105, **tags)
    spy.assert_called_once_with("zishy", 105, child_tags, jot.span)


def test_count_name_tag(jot, mocker):
    spy = mocker.spy(jot.target, "count")
    jot.count("zishy", 105, name="worg")
    spy.assert_called_once_with("zishy", 105, tags(name="worg"), jot.span)


def test_count_value_tag(jot, mocker):
    spy = mocker.spy(jot.target, "count")
    jot.count("zishy", 105, value="worg")
    spy.assert_called_once_with("zishy", 105, tags(value="worg"), jot.span)
