import pytest

import jot as jot_root_module
from jot import facade, log
from jot.base import Meter, Span, Target


@pytest.fixture
def target():
    return Target(log.ALL)


@pytest.fixture(params=[True, False], ids=["with-span", "without-span"])
def active_span(request, target):
    if request.param:
        return Span()


@pytest.fixture(params=[True, False], ids=["facade", "meter"])
def use_facade(request):
    return request.param


@pytest.fixture
def jot(request, target, use_facade, active_span):
    meter = Meter(target, active_span, plonk=42)
    if use_facade:
        old_meter = facade._swap_active(meter)
        yield jot_root_module
        facade._swap_active(old_meter)
    else:
        yield meter


def test_with_span(target, jot, active_span):
    with jot.span("child") as child:
        assert child.active_span.name == "child"
        assert child.active_span is not active_span
        assert isinstance(child.active_span, Span)
        assert child.target is target
        assert not child.active_span.is_finished

    assert child.active_span.is_finished


def test_with_span_error(target, jot, active_span, mocker):
    spy = mocker.spy(target, "error")

    child = None
    with pytest.raises(ValueError) as exc:
        with jot.span("child") as c:
            child = c
            raise ValueError("test error")

    assert str(exc.value) == "test error"

    assert child is not None
    assert child.active_span.is_finished
    spy.assert_called_once_with(
        "Error during child",
        exc.value,
        {"plonk": 42},
        child.active_span,
    )


def test_with_span_tags(jot, tags, assert_tags_are_correct):
    with jot.span("child", **tags) as child:
        assert_tags_are_correct(child)


def test_with_span_name_tag(jot):
    with jot.span("child", name="floopy") as child:
        assert child.tags["name"] == "floopy"


def test_with_span_no_positional_trace_id(jot):
    with pytest.raises(TypeError):
        with jot.span("child", "positional-trace-id"):
            pass
