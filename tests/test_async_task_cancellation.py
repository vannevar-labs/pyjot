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


async def test_decorator_await_cancellation_escapes():
    """
    Test that task cancellation of a decorated function sends cancellation to the decorated function

    When a task running a decorated function is cancelled, the cancellation likely happens
    at the decorator's await asyncio.wait([future]) line. This CancelledError shouldn't
    bubble up and escape. It should instead be contained and re-raised in the child coro such
    that it can handle it naturally.
    """

    handler_was_called = False

    @jot.instrument
    async def function_that_wants_to_handle_async_cancellation():
        nonlocal handler_was_called
        try:
            # This will create a future for the decorator to wait on
            await asyncio.sleep(1.0)  # Long enough to be cancelled
            return "completed"
        except asyncio.CancelledError:
            # This handler should run if cancellation is properly injected into the coroutine
            handler_was_called = True
            raise

    # Create task and cancel it while decorator is waiting
    task = asyncio.create_task(function_that_wants_to_handle_async_cancellation())

    # Give it time to start and reach the decorator's await asyncio.wait([future])
    await asyncio.sleep(0.01)

    # Cancel the task - this cancels the decorator's await asyncio.wait([future])
    task.cancel()

    # The CancelledError should propagate all the way up
    with pytest.raises(asyncio.CancelledError):
        await task

    # This is the key assertion: with the broken decorator, the cancellation
    # happens at await asyncio.wait([future]) and escapes without being
    # injected into the coroutine, so the handler never runs
    assert handler_was_called, (
        "asyncio.CancelledError was not properly injected into the decorated function"
    )


async def test_unhandled_cancellation_bubbles_up():
    """Test that cancellation bubbles up when the decorated function doesn't handle it."""

    @jot.instrument
    async def function_that_ignores_cancellation():
        # No try/except - cancellation should bubble up
        await asyncio.sleep(1.0)
        return "completed"

    task = asyncio.create_task(function_that_ignores_cancellation())
    await asyncio.sleep(0.01)
    task.cancel()

    # Should raise CancelledError since function doesn't handle it
    with pytest.raises(asyncio.CancelledError):
        await task
