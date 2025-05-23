import logging
from os import path

import pytest
from callee.numbers import Integer

import jot
from jot import facade, log, util
from jot.base import Span

IGNORED_TAGS = {"taskName"}


class ExpectedTags:
    def __init__(self, **kwargs):
        self.expected_dict = kwargs

    def __eq__(self, actual_dict):
        filtered_actual = {k: v for k, v in actual_dict.items() if k not in IGNORED_TAGS}
        return self.expected_dict == filtered_actual

    def __repr__(self):
        return f"ExpectedTags({self.expected_dict})"


@pytest.fixture(autouse=True)
def init():
    jot.init(jot.base.Target(level=log.ALL))
    jot.handle_logs("py2jot")
    yield
    jot.ignore_logs("py2jot")


@pytest.fixture
def py2jot():
    logger = logging.getLogger("py2jot")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def jot2py():
    logger = logging.getLogger("jot2py")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def filename():
    return path.basename(__file__)


@pytest.fixture
def info_level():
    old_level = facade.active_meter.target.level
    facade.active_meter.target.level = log.INFO
    yield
    facade.active_meter.target.level = old_level


@pytest.fixture
def spy(mocker):
    spy = mocker.spy(facade.active_meter.target, "log")
    yield spy
    spy.reset_mock()


@pytest.fixture
def span():
    span = Span(
        trace_id=util.generate_trace_id(),
        parent_id=util.generate_span_id(),
        id=util.generate_span_id(),
        name="test-span",
    )
    return span


@pytest.mark.parametrize("level_method_name", ["debug", "info", "warning", "error", "critical"])
def test_jot_via_logger(mocker, py2jot, filename, spy, level_method_name):
    log_function = getattr(py2jot, level_method_name)
    level_name = level_method_name.upper()
    jot_level = getattr(log, level_name)
    log_message = f"test {level_method_name} log message"

    log_function(log_message, extra={"plonk": 42})

    expected_tags = ExpectedTags(
        file=filename,
        line=Integer(),
        function="test_jot_via_logger",
        logger="py2jot",
        plonk="42",
    )
    spy.assert_called_once_with(
        jot_level, log_message, expected_tags, facade.active_meter.active_span
    )


def test_target_accepts_level(mocker, py2jot, spy, info_level):
    py2jot.info("test_message")
    assert spy.call_count == 1


def test_target_ignores_level(mocker, py2jot, spy, info_level):
    py2jot.debug("test_message")
    assert spy.call_count == 0


@pytest.mark.parametrize("level_name", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_log_via_jot(mocker, jot2py, span, level_name):
    spy = mocker.spy(jot2py, "log")
    target = jot.logger.LoggerTarget("jot2py")

    jot_level = getattr(log, level_name)
    py_level = getattr(logging, level_name)
    message = "test message"
    tags = {"plonk": 42}
    target.log(jot_level, message, tags, span)

    expected_tags = {
        **tags,
        "trace_id": util.format_trace_id(span.trace_id),
        "parent_id": util.format_span_id(span.parent_id),
        "span_id": util.format_span_id(span.id),
        "span_name": span.name,
    }
    spy.assert_called_once_with(py_level, message, extra=expected_tags)
