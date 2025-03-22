import pytest

from jot import log
from jot.base import Target, Telemeter

EXPECTED_TAGS = {"plonk": 42}


def tags(**kwtags):
    return {**EXPECTED_TAGS, **kwtags}


@pytest.fixture
def jot():
    target = Target(log.ALL)
    span = target.start()
    return Telemeter(target, span, plonk=42)


def test_finish(jot, mocker):
    sspy = mocker.spy(jot.span, "finish")
    tspy = mocker.spy(jot.target, "finish")

    jot.finish()

    sspy.assert_called_once_with()
    tspy.assert_called_once_with(EXPECTED_TAGS, jot.span)


def test_double_finish(jot, mocker):
    sspy = mocker.spy(jot.span, "finish")
    tspy = mocker.spy(jot.target, "finish")

    jot.finish()

    with pytest.raises(RuntimeError) as excinfo:
        jot.finish()

    assert str(excinfo.value) == "Span is already finished"

    sspy.assert_called_once_with()
    tspy.assert_called_once_with(EXPECTED_TAGS, jot.span)


def test_finish_tags(jot, mocker, tags):
    sspy = mocker.spy(jot.span, "finish")
    tspy = mocker.spy(jot.target, "finish")

    jot.finish(**tags)

    sspy.assert_called_once_with()
    expected_tags = {**EXPECTED_TAGS, **tags}
    tspy.assert_called_once_with(expected_tags, jot.span)


def test_finish_dtags_tag(jot, mocker):
    tspy = mocker.spy(jot.target, "finish")
    jot.finish(dtags="gronk")
    tspy.assert_called_once_with(tags(dtags="gronk"), jot.span)
