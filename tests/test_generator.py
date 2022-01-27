import jot
import pytest
from jot import log
from jot.base import Target

@pytest.fixture(autouse=True)
def init():
    jot.init(Target(level=log.ALL))
    jot.start("test", ctx=1)


# generator with no parameters
@jot.generator("async", ctx=2)
def gen1():
    for i in range(0, 2):
        jot.info("before")
        yield i
        jot.info("after")


# generator with one parameter; may be positional or keyword
@jot.generator("async", ctx=2)
def gen2(arg=None):
    for i in range(0, 2):
        jot.info("before", a=arg)
        yield i
        jot.info("after", a=arg)


# generator with one parameter; keyword only
@jot.generator("async", ctx=2)
def gen3(*, arg):
    for i in range(0, 2):
        jot.info("before", a=arg)
        yield i
        jot.info("after", a=arg)


@jot.tag("thop")
@jot.generator("async", ctx=2)
def gen4(**kwargs):
    for i in range(0, 2):
        jot.info("before", a=kwargs["nilt"])
        yield i
        jot.info("after", a=kwargs["nilt"])


def test_gen1_no_args(mocker):
    spy = mocker.spy(jot.active.target, "log")

    with jot.span("create", ctx=3):
        it = gen1()

    with jot.span("iterate", ctx=4):
        for i in it:
            jot.info("during", i=i)
        jot.info("done")

    for c in spy.mock.mock_calls:
        msg = c.args[1]
        ctx = c.args[2]["ctx"]
        if msg == "before":
            assert ctx == 2
        elif msg == "during":
            assert ctx == 4
        elif msg == "after":
            assert ctx == 2
        elif msg == "done":
            assert ctx == 4
        else:
            raise AssertionError("Unexpected log message")


def test_gen1_tag(mocker):
    spy = mocker.spy(jot.active.target, "log")

    with jot.span("create", ctx=3):
        it = gen1(dynamic=True)

    for i in it:
        jot.info("during", i=i)

    for c in spy.mock.mock_calls:
        msg = c.args[1]
        if msg == "before":
            assert c.args[2]["dynamic"] is True
        elif msg == "during":
            assert "dynamic" not in c.args[2]


def test_gen2_positional_no_tags(mocker):
    spy = mocker.spy(jot.active.target, "log")
    for i in gen2(54):
        jot.info("during", i=i)

    for c in spy.mock.mock_calls:
        msg = c.args[1]
        if msg == "before":
            assert c.args[2]["a"] == 54
        elif msg == "during":
            assert "a" not in c.args[2]


def test_gen2_keyword_no_tags(mocker):
    spy = mocker.spy(jot.active.target, "log")
    for i in gen2(arg=54):
        jot.info("during", i=i)

    for c in spy.mock.mock_calls:
        msg = c.args[1]
        if msg == "before":
            assert c.args[2]["a"] == 54
        elif msg == "during":
            assert "a" not in c.args[2]


def test_gen2_positional_tag(mocker):
    spy = mocker.spy(jot.active.target, "log")
    for i in gen2(54, firth=44):
        jot.info("during", i=i)

    for c in spy.mock.mock_calls:
        msg = c.args[1]
        if msg == "before":
            assert c.args[2]["firth"] == 44
        elif msg == "during":
            assert "firth" not in c.args[2]


def test_gen2_keyword_tag(mocker):
    spy = mocker.spy(jot.active.target, "log")
    for i in gen2(arg=54, firth=44):
        jot.info("during", i=i)

    for c in spy.mock.mock_calls:
        msg = c.args[1]
        if msg == "before":
            assert c.args[2]["firth"] == 44
        elif msg == "during":
            assert "firth" not in c.args[2]


def test_gen3_keyword_no_tags(mocker):
    spy = mocker.spy(jot.active.target, "log")
    for i in gen3(arg=54):
        jot.info("during", i=i)

    for c in spy.mock.mock_calls:
        msg = c.args[1]
        if msg == "before":
            assert c.args[2]["a"] == 54
        elif msg == "during":
            assert "a" not in c.args[2]


def test_gen3_keyword_tag(mocker):
    spy = mocker.spy(jot.active.target, "log")
    for i in gen3(arg=54, firth=44):
        jot.info("during", i=i)

    for c in spy.mock.mock_calls:
        msg = c.args[1]
        if msg == "before":
            assert c.args[2]["firth"] == 44
        elif msg == "during":
            assert "firth" not in c.args[2]


def test_gen4_keyword_no_tags(mocker):
    spy = mocker.spy(jot.active.target, "log")
    for i in gen4(nilt=54):
        jot.info("during", i=i)

    for c in spy.mock.mock_calls:
        msg = c.args[1]
        if msg == "before":
            assert c.args[2]["a"] == 54
        elif msg == "during":
            assert "a" not in c.args[2]


def test_gen4_keyword_declared_tag(mocker):
    spy = mocker.spy(jot.active.target, "log")
    for i in gen4(nilt=54, thop=44):
        jot.info("during", i=i)

    for c in spy.mock.mock_calls:
        msg = c.args[1]
        tags = c.args[2]
        if msg == "before":
            assert tags["a"] == 54
            assert tags["thop"] == 44
        elif msg == "during":
            assert "a" not in tags
            assert "thop" not in tags

def test_tag_unwrapped_function():
    with pytest.raises(RuntimeError) as exc:
        @jot.tag("florn")
        def thefn(): pass

    assert exc.match("thefn\\(\\) isn't decorated by jot")

def test_tag_no_whitelist_necessary():
    with pytest.warns(UserWarning) as w:
        @jot.tag("florn")
        @jot.generator("thefn")
        def thefn(): pass

    assert len(w) == 1
    assert w[0].message.args[0] == "thefn() doesn't need tag decorations"
