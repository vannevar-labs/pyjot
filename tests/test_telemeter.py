import pytest
from jot import Telemeter, log
from jot.base import Span, Target
from jot.print import PrintTarget

EXPECTED_TAGS = {"plonk": 42, "nork": 96}


@pytest.fixture
def jot():
    target = Target(log.ALL)
    span = target.start()
    return Telemeter(target, span, plonk=42)


def test_default_constructor():
    jot = Telemeter()
    assert isinstance(jot.target, Target)
    assert jot.span is None
    assert isinstance(jot.tags, dict)


def test_target_constructor():
    target = PrintTarget()
    jot = Telemeter(target)
    assert jot.target is target
    assert jot.span is None


def test_span_constructor():
    span = Span(1, 2, 3)
    jot = Telemeter(None, span)
    assert isinstance(jot.target, Target)
    assert jot.span is span


def test_tags_constructor():
    jot = Telemeter(None, None, plonk=42, nork=96)
    assert jot.tags["plonk"] == 42
    assert jot.tags["nork"] == 96


def test_start(jot):
    child = jot.start("subtask", nork=96)
    assert len(jot.tags) == 1
    assert child.target is jot.target
    assert child.span is not jot.span
    assert child.tags["plonk"] == 42
    assert child.tags["nork"] == 96


def test_finish(jot, mocker):
    sspy = mocker.spy(jot.span, "finish")
    tspy = mocker.spy(jot.target, "finish")

    jot.finish(nork=96)

    sspy.assert_called_once_with()
    print(tspy.call_args)
    tspy.assert_called_once_with({"plonk": 42, "nork": 96}, jot.span)


def test_debug(jot, mocker):
    spy = mocker.spy(jot.target, "log")
    jot.debug("test log message", nork=96)
    spy.assert_called_once_with(log.DEBUG, "test log message", EXPECTED_TAGS, jot.span)


def test_info(jot, mocker):
    spy = mocker.spy(jot.target, "log")
    jot.info("test log message", nork=96)
    spy.assert_called_once_with(log.INFO, "test log message", EXPECTED_TAGS, jot.span)


def test_warning(jot, mocker):
    spy = mocker.spy(jot.target, "log")
    jot.warning("test log message", nork=96)
    spy.assert_called_once_with(log.WARNING, "test log message", EXPECTED_TAGS, jot.span)


def test_ignored_debug(mocker):
    target = Target(log.NOTHING)
    jot = Telemeter(target)
    spy = mocker.spy(jot.target, "log")
    jot.debug("test log message", nork=96)
    spy.assert_not_called()


def test_ignored_info(mocker):
    target = Target(log.NOTHING)
    jot = Telemeter(target)
    spy = mocker.spy(jot.target, "log")
    jot.info("test log message", nork=96)
    spy.assert_not_called()


def test_ignored_warning(mocker):
    target = Target(log.NOTHING)
    jot = Telemeter(target)
    spy = mocker.spy(jot.target, "log")
    jot.warning("test log message", nork=96)
    spy.assert_not_called()


def test_error(jot, mocker):
    spy = mocker.spy(jot.target, "error")
    try:
        4 / 0
    except ZeroDivisionError as e:
        jot.error("caught test error", e, nork=96)
        spy.assert_called_once_with("caught test error", e, EXPECTED_TAGS, jot.span)


def test_magnitude(jot, mocker):
    spy = mocker.spy(jot.target, "magnitude")
    jot.magnitude("zishy", 105, nork=96)
    spy.assert_called_once_with("zishy", 105, EXPECTED_TAGS, jot.span)


def test_count(jot, mocker):
    spy = mocker.spy(jot.target, "count")
    jot.count("zishy", 105, nork=96)
    spy.assert_called_once_with("zishy", 105, EXPECTED_TAGS, jot.span)
