import pytest

from jot import log
from jot.base import Meter, Span, Target
from jot.print import PrintTarget


@pytest.fixture
def target():
    return Target(log.ALL)


def test_default_constructor():
    jot = Meter()
    assert isinstance(jot.target, Target)
    assert jot.active_span is None
    assert isinstance(jot.tags, dict)
    assert len(jot.tags) == 0


def test_default_constructor_tags(tags, assert_tags_are_correct):
    jot = Meter(None, None, **tags)
    assert isinstance(jot.target, Target)
    assert jot.active_span is None
    assert_tags_are_correct(jot)


def test_target_constructor():
    target = PrintTarget()
    jot = Meter(target)
    assert jot.target is target
    assert jot.active_span is None


def test_target_constructor_tags(tags, assert_tags_are_correct):
    target = PrintTarget()
    jot = Meter(target, None, **tags)
    assert jot.target is target
    assert jot.active_span is None
    assert_tags_are_correct(jot)


def test_span_constructor():
    span = Span(1, 2, 3)
    jot = Meter(None, span)
    assert isinstance(jot.target, Target)
    assert jot.active_span is span


def test_span_constructor_tags(tags, assert_tags_are_correct):
    span = Span(1, 2, 3)
    jot = Meter(None, span, **tags)
    assert isinstance(jot.target, Target)
    assert jot.active_span is span
    assert_tags_are_correct(jot)


def test_target_tag():
    jot = Meter(target="plict")
    assert jot.tags["target"] == "plict"


def test_span_tag():
    jot = Meter(span="plict")
    assert jot.tags["span"] == "plict"
