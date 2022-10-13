import jot
import pytest
from jot import log
from jot.base import Span, Target, Telemeter


@pytest.fixture
def assert_forwards(mocker):
    def _assert_forwards(method_name, *args, **kwargs):
        # spy on the method
        spy = mocker.spy(jot.active, method_name)

        # call the method
        func = getattr(jot, method_name)
        func(*args, **kwargs)

        # assert the call was forwarded
        spy.assert_called_once_with(*args, **kwargs)

    return _assert_forwards


@pytest.fixture(autouse=True)
def init():
    jot.init(Target(level=log.ALL))
    jot.start("test", ctx=1)


def test_active():
    assert isinstance(jot.active, Telemeter)


def test_init():
    target = Target()
    jot.init(target)
    assert jot.active.target is target
    assert jot.active.tags == {}
    assert jot.active.span is None


def test_init_tags(dtags, kwtags, assert_tags_are_correct):
    target = Target()
    jot.init(target, dtags, **kwtags)
    assert_tags_are_correct(jot.active)


def test_start():
    jot.init(Target(), loozy=34)
    parent = jot.active
    jot.start("child")

    assert jot.active is not parent
    assert isinstance(jot.active.span.trace_id, bytes)
    assert isinstance(jot.active.span.id, bytes)
    assert jot.active.span.name == "child"


def test_start_tags(dtags, kwtags, assert_child_tags_are_correct):
    jot.init(Target(), loozy=34)
    parent = jot.active
    jot.start("child", dtags, **kwtags)
    assert_child_tags_are_correct(parent, jot.active)


def test_finish():
    parent = jot.active
    jot.start("child")
    jot.finish()

    assert jot.active is parent


def test_finish_forwards(assert_forwards):
    parent = jot.active
    jot.start("child")
    assert_forwards("finish")


def test_with():
    parent = jot.active
    with jot.span("child", lep=66) as child:
        assert child is jot.active
        assert child is not parent
        assert child.span.parent_id == parent.span.id
        assert child.tags["lep"] == 66
    assert jot.active is parent


def test_with_trace_id():
    parent = jot.active
    with jot.span("child", trace_id=51) as child:
        assert child is jot.active
        assert child is not parent
        assert child.span.trace_id == 51
        assert child.span.parent_id is None
        assert isinstance(child.span.id, bytes)
        assert child.span.name == "child"


def test_with_parent_id():
    with jot.span("child", trace_id=51, parent_id=66) as child:
        assert child is jot.active
        assert child.span.trace_id == 51
        assert child.span.parent_id == 66
        assert isinstance(child.span.id, bytes)
        assert child.span.name == "child"


def test_with_error(mocker):
    spy = mocker.spy(jot.active.target, "error")

    try:
        with jot.span("child", nork=6):
            1 / 0
    except ZeroDivisionError:
        pass

    spy.assert_called_once()
    assert spy.call_args.args[0] == "Error during child"
    assert isinstance(spy.call_args.args[1], ZeroDivisionError)
    assert spy.call_args.args[2]["nork"] == 6
    assert isinstance(spy.call_args.args[3], Span)
    assert spy.call_args.args[3].parent_id == jot.active.span.id


def test_event(assert_forwards):
    assert_forwards("event", "name", {"plonk": 96}, bink=42)


def test_debug(assert_forwards):
    assert_forwards("debug", "debug message", {"plonk": 96}, bink=42)


def test_info(assert_forwards):
    assert_forwards("info", "info message", {"plonk": 96}, bink=42)


def test_warning(assert_forwards):
    assert_forwards("warning", "warning message", {"plonk": 96}, bink=42)


def test_error(assert_forwards):
    try:
        1 / 0
    except ZeroDivisionError as exc:
        assert_forwards("error", "error message", exc, {"plonk": 96}, bink=42)


def test_magnitude(assert_forwards):
    assert_forwards("magnitude", "temperature", 99.0, {"plonk": 96}, bink=42)


def test_count(assert_forwards):
    assert_forwards("count", "requests", 99, {"plonk": 96}, bink=42)
