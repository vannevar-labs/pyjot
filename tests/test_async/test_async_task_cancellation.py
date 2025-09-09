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


async def test_nested_cancellation_should_not_bubble_up():
    """
    Test that cancellation errors from nested async functions should not bubble
    up to the decorated function, but should be handled at the child site.
    """
    inner_cancelled = False
    outer_cancelled = False

    async def inner_task():
        nonlocal inner_cancelled
        try:
            await asyncio.sleep(10)  # Long sleep to ensure cancellation
        except asyncio.CancelledError:
            inner_cancelled = True
            raise  # Re-raise to let caller handle it

    @jot.instrument
    async def outer_task():
        nonlocal outer_cancelled
        try:
            task = asyncio.create_task(inner_task())
            await asyncio.sleep(0.1)  # Give task time to start
            task.cancel()  # Cancel the inner task

            try:
                await task
            except asyncio.CancelledError:
                # This should handle the cancellation locally
                pass

            return "completed"
        except asyncio.CancelledError:
            outer_cancelled = True
            raise

    # Run the outer task
    result = await outer_task()

    # The inner task should have been cancelled
    assert inner_cancelled, "Inner task should have been cancelled"

    # The outer task should NOT have been cancelled
    assert not outer_cancelled, "Outer task should not have been cancelled"
    assert result == "completed", "Outer task should have completed normally"


async def test_shield_should_protect_from_cancellation():
    """
    Test that asyncio.shield should protect a task from cancellation,
    even when using the jot decorator.
    """
    task_completed = False
    shield_worked = False

    @jot.instrument
    async def protected_task():
        nonlocal task_completed
        await asyncio.sleep(0.2)  # Simulate some work
        task_completed = True
        return "task completed"

    @jot.instrument
    async def caller_task():
        nonlocal shield_worked
        try:
            # Shield the task from cancellation
            result = await asyncio.wait_for(
                asyncio.shield(protected_task()),
                timeout=0.1,  # This will timeout before task completes
            )
            return result
        except asyncio.TimeoutError:
            # Shield should protect the task, so we get TimeoutError not CancelledError
            shield_worked = True

            # Give the shielded task time to complete
            await asyncio.sleep(0.2)
            return "timeout handled"

    # Run the caller task
    result = await caller_task()

    # The shield should have worked (we got TimeoutError, not CancelledError)
    assert shield_worked, "Shield should have protected from cancellation"

    # The protected task should have completed despite the timeout
    assert task_completed, "Protected task should have completed"
    assert result == "timeout handled", "Caller should have handled timeout"


async def test_cancellation_should_bubble_up_when_not_handled():
    """
    Test that cancellation errors should properly bubble up when NOT handled
    locally. This ensures we don't accidentally swallow all cancellations.
    """
    inner_cancelled = False
    outer_cancelled = False

    async def inner_task():
        nonlocal inner_cancelled
        try:
            await asyncio.sleep(10)  # Long sleep to ensure cancellation
        except asyncio.CancelledError:
            inner_cancelled = True
            raise  # Re-raise to let caller handle it

    @jot.instrument
    async def outer_task():
        nonlocal outer_cancelled
        try:
            task = asyncio.create_task(inner_task())
            await asyncio.sleep(0.1)  # Give task time to start
            task.cancel()  # Cancel the inner task

            # NO try/except here - cancellation should bubble up
            await task

            return "completed"
        except asyncio.CancelledError:
            outer_cancelled = True
            raise

    # Run the outer task and expect it to be cancelled
    with pytest.raises(asyncio.CancelledError):
        await outer_task()

    # The inner task should have been cancelled
    assert inner_cancelled, "Inner task should have been cancelled"

    # The outer task should ALSO have been cancelled (no local handling)
    assert outer_cancelled, "Outer task should have been cancelled too"
