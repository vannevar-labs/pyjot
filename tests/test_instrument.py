import asyncio

import pytest

import jot
from jot import facade, log
from jot.base import Target


async def wait_for(awaitable):
    done, pending = await asyncio.wait([awaitable])
    return done.pop().result()


@pytest.fixture(autouse=True)
def root_span():
    root = jot.span("root")
    old = facade._swap_active(root)
    yield root.active_span
    facade._swap_active(old)


@pytest.fixture
def target():
    return Target(level=log.ALL)


@pytest.fixture(autouse=True)
def init(target):
    jot.init(target)


@pytest.fixture
def logspy(target, mocker):
    spy = mocker.spy(target, "log")
    return spy


@pytest.fixture
def errspy(target, mocker):
    spy = mocker.spy(target, "error")
    return spy


@pytest.mark.reject("throws")
def test_sync_log(func, args, kwargs, root_span, logspy):
    func(*args, **kwargs)

    # check logs
    call = logspy.call_args_list[0]
    span = call.args[3]

    assert call.args[1] == "running"
    assert call.args[2]["ord"] == 1
    assert span.name == func.__name__
    assert span.trace_id is not None
    assert span.parent_id == root_span.id

    # sync functions only log once
    assert logspy.call_count == 1


@pytest.mark.select("tag_one")
def test_called_with_tag_one(func, args, kwargs, logspy):
    func(*args, **kwargs)

    # all running logs have tag_one
    running = [c.args[2] for c in logspy.call_args_list if c.args[1] == "running"]
    for r in running:
        assert r["tag_one"] == 1


@pytest.mark.select("tag_two")
def test_called_with_tags(func, args, kwargs, logspy):
    func(*args, **kwargs)

    # all running logs have tag_two
    running = [c.args[2] for c in logspy.call_args_list if c.args[1] == "running"]
    for r in running:
        assert r["tag_two"] == 2


@pytest.mark.select("throws")
def test_throws(func, args, kwargs, logspy, errspy):
    # the function throws an exception
    with pytest.raises(Exception):
        func(*args, **kwargs)

    # the error is reported
    assert errspy.call_count == 1
    c = errspy.call_args_list[0]
    assert c.args[0] == f"Error during {c.args[3].name}"


@pytest.mark.reject("throws")
async def test_async_call(func, args, kwargs, root_span, logspy):
    coro = func(*args, **kwargs)

    jot.info("suspended", ord=1)
    result = await coro
    jot.info("suspended", ord=2)

    assert result == "done"

    # all the suspended logs are done by the root span
    suspended = [c.args[3] for c in logspy.call_args_list if c.args[1] == "suspended"]
    for s in suspended:
        assert s is root_span

    # all the running logs are done by the child span
    running = [c.args[3] for c in logspy.call_args_list if c.args[1] == "running"]
    for r in running:
        assert r is not root_span
        assert r.name == func.__name__
        assert r.parent_id == root_span.id


@pytest.mark.reject("throws")
async def test_async_send(func, args, kwargs, root_span, logspy):
    result = None
    ord = 1
    try:
        coro = func(*args, **kwargs)
        jot.info("suspended", ord=1)
        future = coro.send(None)
        while True:
            ord += 1
            jot.info("suspended", ord=ord)
            value = await wait_for(future)
            future = coro.send(value)
    except StopIteration as e:
        result = e.value
    finally:
        jot.info("suspended", ord=ord)

    assert result == "done"

    # all the suspended logs are done by the root span
    suspended = [c.args[3] for c in logspy.call_args_list if c.args[1] == "suspended"]
    assert len(suspended) >= 2
    for s in suspended:
        assert s is root_span

    # all the running logs are done by the child span
    running = [c.args[3] for c in logspy.call_args_list if c.args[1] == "running"]
    assert len(running) >= 1
    for r in running:
        assert r is not root_span
        assert r.name == func.__name__
        assert r.parent_id == root_span.id


@pytest.mark.select("tag_one")
async def test_async_tag_one(func, args, kwargs, logspy):
    await func(*args, **kwargs)

    # all the logs have tag_one
    for c in logspy.call_args_list:
        assert c.args[2]["tag_one"] == 1


@pytest.mark.select("tag_two")
async def test_async_tag_two(func, args, kwargs, logspy):
    await func(*args, **kwargs)

    # all the logs have tag_two
    for c in logspy.call_args_list:
        assert c.args[2]["tag_two"] == 2

@pytest.mark.select("error_propagation")
async def test_async_error_handled(func, logspy, errspy):

    # the outer function calls inner_throws, which raises an error. Outer catches it, so it should
    # not propagate to this test.
    try:
        await func()
    except Exception as e:
        print(f"Caught exception: {type(e).__name__}: {e}")

    # check logs
    args = logspy.call_args_list[0][0]
    assert args[1] == "outer before"
    assert args[2]['ord'] == 1

    args = logspy.call_args_list[1][0]
    assert args[1] == "middle before"
    assert args[2]['ord'] == 2

    args = logspy.call_args_list[2][0]
    assert args[1] == "inner before"
    assert args[2]['ord'] == 3

    args = logspy.call_args_list[3][0]
    assert args[1] == "fail before"
    assert args[2]['ord'] == 4

    args = logspy.call_args_list[4][0]
    assert args[1] == "middle caught"
    assert args[2]['ord'] == 5

    args = logspy.call_args_list[5][0]
    assert args[1] == "outer after"
    assert args[2]['ord'] == 6
