import asyncio

import pytest

import jot
from jot import facade, log
from jot.base import Target

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


@jot.instrument
async def outer():
    jot.info("outer before", ord=1)
    await middle()
    jot.info("outer after", ord=6)

async def middle():
    try:
        jot.info("middle before", ord=2)
        await inner()
        jot.info("middle after", ord=-1)
    except RuntimeError as e:
        jot.info("middle caught", ord=5, error=e)

async def inner():
    jot.info("inner before", ord=3)
    coro = fail()
    task = asyncio.create_task(coro)
    await task
    jot.info("inner after", ord=-1)

async def fail():
    jot.info("fail before", ord=4)
    await asyncio.sleep(0.01)
    raise RuntimeError("oops")

async def test_async_error_handled(logspy, errspy):

    # the outer function calls inner_throws, which raises an error. Outer catches it, so it should
    # not propagate to this test.
    try:
        await outer()
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

    # check errors
    assert errspy.call_count == 0
