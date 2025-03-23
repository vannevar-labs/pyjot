import pytest

from jot import log
from jot.base import Meter, Target


@pytest.fixture
def jot():
    target = Target(log.ALL)
    return Meter(target, None, plonk=42)


def test_start(jot, mocker):
    spy = mocker.spy(jot.target, "start")
    with pytest.raises(RuntimeError) as excinfo:
        jot.start()
    assert str(excinfo.value) == "No active span to start"
    spy.assert_not_called()


def test_start_child(jot, mocker):
    child = jot.start("child")
    assert child is not jot
    assert child.active_span is not None
    assert child.active_span.is_started
    assert not child.active_span.is_finished


def test_finish(jot, mocker):
    spy = mocker.spy(jot.target, "finish")
    with pytest.raises(RuntimeError) as excinfo:
        jot.finish()
    assert str(excinfo.value) == "No active span to finish"
    spy.assert_not_called()
