import pytest
import sentry_sdk as sdk

from jot import log, util
from jot.base import Span
from jot.sentry import SentryTarget

DSN = "http://241cc27aee334e039477db937c7adeae@test.example.com/1277190904802156"
ENV_NAME = "jot-testing"


@pytest.fixture
def target():
    return SentryTarget(dsn=DSN, environment=ENV_NAME)


@pytest.fixture
def span():
    span = Span(name="test-root")
    span.start()
    return span


def test_constructor_args(target):
    assert sdk.Hub.current.client.options["dsn"] == DSN
    assert sdk.Hub.current.client.options["environment"] == ENV_NAME


def test_start_root(target, span, mocker):
    mock = mocker.patch("sentry_sdk.start_transaction")
    target.start({}, span)

    mock.assert_called_once()
    assert mock.call_args.args == ()
    assert mock.call_args.kwargs == {
        "op": "test-root",
        "name": "test-root",
        "trace_id": util.format_trace_id(span.trace_id),
        "span_id": util.format_span_id(span.id),
        "same_process_as_parent": False,
    }
    assert target.spans[span.id] == mock.return_value


def test_start_child(target, span, mocker):
    target.start({}, span)
    mock = mocker.patch.object(target.spans[span.id].__class__, "start_child")
    child = Span(name="test-child", trace_id=span.trace_id, parent_id=span.id)
    target.start({}, child)

    mock.assert_called_once()
    assert mock.call_args.args == ()
    assert mock.call_args.kwargs == {
        "op": "test-child",
        "description": "test-child",
        "span_id": util.format_span_id(child.id),
        "same_process_as_parent": True,
    }
    assert target.spans[child.id] == mock.return_value


def test_finish(target, span, mocker):
    target.start({}, span)
    mock = mocker.patch.object(target.spans[span.id].__class__, "finish")
    sentry_span = target.spans[span.id]
    target.finish({"nork": 21}, span)

    assert sentry_span._tags["nork"] == 21
    mock.assert_called_once()
    assert mock.call_args.args == ()
    assert mock.call_args.kwargs == {}


def test_log(target, mocker):
    mock = mocker.patch("sentry_sdk.capture_message")
    target.log(log.WARNING, "test message", {"plonk": 55})

    mock.assert_called_once()
    assert mock.call_args.args == ("test message",)
    assert mock.call_args.kwargs == {"level": "warning", "contexts": None, "tags": {"plonk": 55}}


def test_error(target, span, mocker):
    mock = mocker.patch("sentry_sdk.capture_exception")
    exception = Exception("test exception")
    target.error("test message", exception, {"plonk": 55}, span)

    mock.assert_called_once()
    assert mock.call_args.args[0] == exception
    assert mock.call_args.kwargs == {
        "level": "error",
        "contexts": {
            "trace": {
                "trace_id": util.format_trace_id(span.trace_id),
                "span_id": util.format_span_id(span.id),
                "op": span.name,
            }
        },
        "extras": {"message": "test message"},
        "tags": {"plonk": 55},
    }
