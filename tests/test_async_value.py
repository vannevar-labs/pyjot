import asyncio

import pytest
import time
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
    return await middle()

async def middle():
    f = inner()
    value = await f
    return value

def inner():
    loop = asyncio.get_running_loop()
    f = loop.run_in_executor(None, simulate_io)
    return f

def simulate_io():
    time.sleep(0.01)
    return "value from io"

# This test checks that the value from the inner function is correctly propagated through the async
# calls. Interestingly, it passes even when the relavant lines in decorators.py are commented out.
# This seems to be undefined behavior in the asyncio event loop. PEP 492 is vague about what happens
# when you call send() on a coroutine. The answer appears to be that the coroutine is resumed, but
# the value passed to send() is ignored. The pending `await` resolves with whatever value the
# underlying future resolves to.
async def test_async_value_propagation(errspy):
    result = await outer()
    print(f"Result: {result}")
    assert result == "value from io"
    assert errspy.call_count == 0
