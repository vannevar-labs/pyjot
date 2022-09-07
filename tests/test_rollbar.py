import sys
import pytest
import rollbar

from jot import log
from jot.rollbar import RollbarTarget


@pytest.fixture
def target():
    return RollbarTarget("test_access_token", "test_environment", capture_ip=False)


@pytest.fixture
def logging(target):
    target.level = log.ALL
    yield target
    target.level = log.NOTHING


# This test has to run before rollbar is initialized, which will happen
# the first time the RollbarTarget constructure is called with an access_token
@pytest.mark.order("first")
def test_no_access_token():
    with pytest.raises(RuntimeError) as exc:
        RollbarTarget()

    assert exc.match("Please supply your access token")


def test_access_token_optional(target):
    RollbarTarget()


def test_different_access_token(target):
    with pytest.raises(RuntimeError) as exc:
        RollbarTarget("test_access_token2")

    assert exc.match("Rollbar can only use one access token at a time")


def test_constructor_args(target):
    assert rollbar.SETTINGS["access_token"] == "test_access_token"
    assert rollbar.SETTINGS["environment"] == "test_environment"
    assert rollbar.SETTINGS["capture_ip"] is False


def test_log(logging, mocker):
    mock = mocker.patch("rollbar.report_message")
    logging.log(log.WARNING, "test message", {"plonk": 55})

    mock.assert_called_once()
    assert mock.call_args.args == ("test message", "warning", None, {"plonk": 55})
    assert mock.call_args.kwargs == {}


def test_error(target, mocker):
    mock = mocker.patch("rollbar.report_exc_info")

    try:
        1 / 0
    except Exception as e:
        info = sys.exc_info()
        target.error("Failed", e, {"nork": "nob"})

    mock.assert_called_once()
    assert mock.call_args.args == (info, None, {"nork": "nob", "message": "Failed"})
    assert mock.call_args.kwargs == {"level": "error"}
