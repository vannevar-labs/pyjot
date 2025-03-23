import inspect

import pytest
from callee.numbers import Integer

import jot
from jot import facade, log
from jot.base import Meter, Target


def caller_tags(**kwtags):
    frame = inspect.currentframe()
    frame = frame.f_back
    return {
        **kwtags,
        "file": __file__,
        "line": Integer(),
        "function": frame.f_code.co_name,
    }


@pytest.fixture
def assert_forwards(mocker):
    def _assert_forwards(method_name, *args, **kwargs):
        # spy on the method
        spy = mocker.spy(facade.active_meter, method_name)

        # call the method
        func = getattr(jot, method_name)
        func(*args, **kwargs)

        # assert the call was forwarded
        spy.assert_called_once_with(*args, **kwargs)

    return _assert_forwards


@pytest.fixture
def log_spy(mocker):
    return mocker.spy(facade.active_meter.target, "log")


@pytest.fixture(autouse=True)
def init():
    jot.init(Target(level=log.ALL))
    jot.start("test", ctx=1)


@pytest.fixture
def root():
    return jot.start("test", ctx=1)


def test_rootless():
    child = jot.start("child")
    assert child.active_span.parent_id is None


def test_active_meter():
    assert isinstance(facade.active_meter, Meter)


def test_init():
    target = Target()
    jot.init(target)
    assert facade.active_meter.target is target
    assert facade.active_meter.tags == {}
    assert facade.active_meter.active_span is None


def test_init_tags(tags, assert_tags_are_correct):
    target = Target()
    jot.init(target, **tags)
    assert_tags_are_correct(facade.active_meter)


def test_init_dtag_tag():
    target = Target()
    jot.init(target, dtags="lorf")
    assert facade.active_meter.tags == {"dtags": "lorf"}


def test_start():
    jot.init(Target(), loozy=34)
    parent = facade.active_meter
    child = jot.start("child")

    assert facade.active_meter is parent
    assert child is not parent
    assert child.active_span is not None
    assert isinstance(child.active_span.trace_id, bytes)
    assert child.active_span.parent_id is None
    assert isinstance(child.active_span.id, bytes)
    assert child.active_span.name == "child"


def test_start_tags(tags, assert_child_tags_are_correct):
    jot.init(Target(), loozy=34)
    child = jot.start("child", **tags)
    assert_child_tags_are_correct(facade.active_meter, child)


def test_finish(assert_forwards):
    with pytest.raises(RuntimeError) as excinfo:
        jot.finish()
    assert str(excinfo.value) == "No active span to finish"


def test_finish_rooted(assert_forwards):
    child = jot.start("child")
    jot.facade._swap_active(child)
    assert_forwards("finish", bink=42)


def test_event(assert_forwards):
    assert_forwards("event", "name", bink=42)


def test_debug(assert_forwards):
    assert_forwards("debug", "debug message", bink=42)


def test_info(assert_forwards):
    assert_forwards("info", "info message", bink=42)


def test_warning(assert_forwards):
    assert_forwards("warning", "warning message", bink=42)


def test_error(assert_forwards):
    try:
        1 / 0
    except ZeroDivisionError as exc:
        assert_forwards("error", "error message", exc, bink=42)


def test_magnitude(assert_forwards):
    assert_forwards("magnitude", "temperature", 99.0, bink=42)


def test_count(assert_forwards):
    assert_forwards("count", "requests", 99, bink=42)


def test_debug_caller(log_spy):
    jot.debug("message")
    log_spy.assert_called_once_with(log.DEBUG, "message", caller_tags(), None)


def test_info_caller(log_spy):
    jot.info("message")
    log_spy.assert_called_once_with(log.INFO, "message", caller_tags(), None)


def test_warning_caller(log_spy):
    jot.warning("message")
    log_spy.assert_called_once_with(log.WARNING, "message", caller_tags(), None)


def test_debug_caller_rooted(root, log_spy):
    root.debug("message")
    log_spy.assert_called_once_with(log.DEBUG, "message", caller_tags(ctx=1), root.active_span)


def test_info_caller_rooted(root, log_spy):
    root.info("message")
    log_spy.assert_called_once_with(log.INFO, "message", caller_tags(ctx=1), root.active_span)


def test_warning_caller_rooted(root, log_spy):
    root.warning("message")
    log_spy.assert_called_once_with(log.WARNING, "message", caller_tags(ctx=1), root.active_span)
