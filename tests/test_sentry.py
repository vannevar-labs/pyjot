import pytest

from jot import log
from jot.sentry import SentryTarget
import sentry_sdk as sdk

DSN = "http://241cc27aee334e039477db937c7adeae@test.example.com/1277190904802156"
ENV_NAME = "jot-testing"


@pytest.fixture
def target():
    return SentryTarget(dsn=DSN, environment=ENV_NAME)


def test_constructor_args(target):
    assert sdk.Hub.current.client.options["dsn"] == DSN
    assert sdk.Hub.current.client.options["environment"] == ENV_NAME


def test_start_root(target, mocker):
    mock = mocker.patch("sentry_sdk.start_transaction")
    span = target.start(name="test-root")

    mock.assert_called_once()
    assert mock.call_args.args == ()
    assert mock.call_args.kwargs == {
        "op": "test-root",
        "name": "test-root",
        "trace_id": span.trace_id_hex,
        "parent_span_id": None,
        "span_id": span.id_hex,
        "same_process_as_parent": None
    }
    assert target.spans[span.id] == mock.return_value


def test_start_child(target, mocker):
    parent = target.start(name="test-parent")
    mock = mocker.patch.object(target.spans[parent.id].__class__, "start_child")
    child = target.start(name="test-child", trace_id=parent.trace_id, parent_id=parent.id)

    mock.assert_called_once()
    assert mock.call_args.args == ()
    assert mock.call_args.kwargs == {
        "op": "test-child",
        "description": "test-child",
        "span_id": child.id_hex,
        "same_process_as_parent": True
    }
    assert target.spans[child.id] == mock.return_value


def test_finish(target, mocker):
    span = target.start(name="test-span")
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
    assert mock.call_args.kwargs == {
        "level": "warning",
        "contexts": None,
        "tags": {"plonk": 55}
    }


def test_error(target, mocker):
    mock = mocker.patch("sentry_sdk.capture_exception")
    exception = Exception("test exception")
    span = target.start(name="test-span")
    target.error("test message", exception, {"plonk": 55}, span)

    mock.assert_called_once()
    assert mock.call_args.args[0] == exception
    assert mock.call_args.kwargs == {
        "level": "error",
        "contexts": {
            "trace": {
                "trace_id": span.trace_id_hex,
                "span_id": span.id_hex,
                "op": span.name
            }
        },
        "extras": {"message": "test message"},
        "tags": {"plonk": 55}
    }
