import pytest
from jot import Jot, log
from jot.base import Span, Target
from jot.print import PrintTarget

EXPECTED_TAGS = {"plonk": 42, "nork": 96}


@pytest.fixture
def jot():
    target = Target(log.ALL)
    return Jot(target, None, {"plonk": 42})


def test_default_constructor():
    jot = Jot()
    assert isinstance(jot.target, Target)
    assert isinstance(jot.span, Span)
    assert isinstance(jot.tags, dict)


def test_target_constructor():
    target = PrintTarget()
    jot = Jot(target)
    assert jot.target is target
    assert isinstance(jot.span, Span)


def test_span_constructor():
    span = Span(1, 2, 3)
    jot = Jot(None, span)
    assert isinstance(jot.target, Target)
    assert jot.span is span


def test_tags_constructor():
    jot = Jot(None, None, {"plonk": 42}, {"nork": 96})
    assert jot.tags["plonk"] == 42
    assert jot.tags["nork"] == 96


def test_start(jot):
    child = jot.start("subtask", {"nork": 96})
    assert len(jot.tags) == 1
    assert child.target is jot.target
    assert child.span is not jot.span
    assert child.tags["plonk"] == 42
    assert child.tags["nork"] == 96


def test_finish(jot, mocker):
    sspy = mocker.spy(jot.span, "finish")
    tspy = mocker.spy(jot.target, "finish")

    jot.finish({"nork": 96})

    sspy.assert_called_once_with()
    tspy.assert_called_once_with(jot.span, {"plonk": 42, "nork": 96})


def test_debug(jot, mocker):
    spy = mocker.spy(jot.target, "log")
    jot.debug("test log message", {"nork": 96})
    spy.assert_called_once_with(jot.span, log.DEBUG, "test log message", EXPECTED_TAGS)


def test_info(jot, mocker):
    spy = mocker.spy(jot.target, "log")
    jot.info("test log message", {"nork": 96})
    spy.assert_called_once_with(jot.span, log.INFO, "test log message", EXPECTED_TAGS)


def test_warning(jot, mocker):
    spy = mocker.spy(jot.target, "log")
    jot.warning("test log message", {"nork": 96})
    spy.assert_called_once_with(jot.span, log.WARNING, "test log message", EXPECTED_TAGS)

def test_ignored_debug(mocker):
    target = Target(log.NOTHING)
    jot = Jot(target)
    spy = mocker.spy(jot.target, "log")
    jot.debug("test log message", {"nork": 96})
    spy.assert_not_called()

def test_ignored_info(mocker):
    target = Target(log.NOTHING)
    jot = Jot(target)
    spy = mocker.spy(jot.target, "log")
    jot.info("test log message", {"nork": 96})
    spy.assert_not_called()

def test_ignored_warning(mocker):
    target = Target(log.NOTHING)
    jot = Jot(target)
    spy = mocker.spy(jot.target, "log")
    jot.warning("test log message", {"nork": 96})
    spy.assert_not_called()


def test_error(jot, mocker):
    spy = mocker.spy(jot.target, "error")
    try:
        4 / 0
    except ZeroDivisionError as e:
        jot.error("caught test error", e, {"nork": 96})
        spy.assert_called_once_with(jot.span, "caught test error", e, EXPECTED_TAGS)


def test_magnitude(jot, mocker):
    spy = mocker.spy(jot.target, "magnitude")
    jot.magnitude("zishy", 105, {"nork": 96})
    spy.assert_called_once_with(jot.span, "zishy", 105, EXPECTED_TAGS)


def test_count(jot, mocker):
    spy = mocker.spy(jot.target, "count")
    jot.count("zishy", 105, {"nork": 96})
    spy.assert_called_once_with(jot.span, "zishy", 105, EXPECTED_TAGS)
