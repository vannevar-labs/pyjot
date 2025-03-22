import pytest

from jot import log
from jot.base import Target, Telemeter


@pytest.fixture
def jot():
    target = Target(log.ALL)
    return Telemeter(target, None, plonk=42)


def test_finish(jot, mocker):
    spy = mocker.spy(jot.target, "finish")
    with pytest.raises(RuntimeError) as excinfo:
        jot.finish()
    assert str(excinfo.value) == "No active span to finish"
    spy.assert_not_called()
