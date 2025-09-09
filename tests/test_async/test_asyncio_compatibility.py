import asyncio
import contextvars

import pytest

from jot.decorators import instrument


class TestAsyncioCompatibility:
    """Test suite for asyncio compatibility with the jot decorator"""

    async def test_context_variables_propagation(self):
        """Test that context variables work correctly with decorated functions"""
        test_var = contextvars.ContextVar("test_var", default="not set")

        @instrument
        async def decorated_task(suffix):
            # Should see the context variable value
            initial = test_var.get()
            await asyncio.sleep(0.01)
            test_var.set(f"modified in {suffix}")
            return initial, test_var.get()

        async def normal_task(suffix):
            initial = test_var.get()
            await asyncio.sleep(0.01)
            test_var.set(f"modified in {suffix}")
            return initial, test_var.get()

        # Test normal task
        test_var.set("initial value")
        normal_initial, normal_final = await normal_task("normal")
        normal_outside = test_var.get()

        # Reset context and test decorated task
        test_var.set("initial value")
        decorated_initial, decorated_final = await decorated_task("decorated")
        decorated_outside = test_var.get()

        # Both should behave the same way
        assert normal_initial == decorated_initial == "initial value"
        assert normal_final == "modified in normal"
        assert decorated_final == "modified in decorated"
        assert normal_outside == "modified in normal"
        assert decorated_outside == "modified in decorated"

    async def test_task_groups_with_exceptions(self):
        """Test that TaskGroups work correctly with decorated functions"""

        @instrument
        async def failing_task(delay, name):
            await asyncio.sleep(delay)
            raise ValueError(f"Task {name} failed")

        @instrument
        async def succeeding_task(delay, name):
            await asyncio.sleep(delay)
            return f"Task {name} succeeded"

        # Test with Python 3.11+ TaskGroup if available
        if hasattr(asyncio, "TaskGroup"):
            try:
                # Import ExceptionGroup for Python 3.11+
                from builtins import ExceptionGroup

                with pytest.raises(ExceptionGroup) as exc_info:
                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(succeeding_task(0.01, "A"))
                        tg.create_task(failing_task(0.02, "B"))
                        tg.create_task(succeeding_task(0.015, "C"))

                # Should have caught the ValueError in an ExceptionGroup
                assert len(exc_info.value.exceptions) == 1
                assert isinstance(exc_info.value.exceptions[0], ValueError)
                assert "Task B failed" in str(exc_info.value.exceptions[0])
            except ImportError:
                # Skip test on Python < 3.11
                pytest.skip("TaskGroup and ExceptionGroup require Python 3.11+")

    async def test_gather_exception_handling(self):
        """Test that asyncio.gather works correctly with decorated functions"""

        @instrument
        async def failing_task(delay):
            await asyncio.sleep(delay)
            raise ValueError("Task failed")

        @instrument
        async def succeeding_task(delay):
            await asyncio.sleep(delay)
            return "success"

        # Test return_exceptions=True
        results = await asyncio.gather(
            succeeding_task(0.01), failing_task(0.01), succeeding_task(0.01), return_exceptions=True
        )

        assert results[0] == "success"
        assert isinstance(results[1], ValueError)
        assert results[2] == "success"

        # Test exception propagation
        with pytest.raises(ValueError):
            await asyncio.gather(succeeding_task(0.01), failing_task(0.01), return_exceptions=False)

    async def test_semaphore_and_locks(self):
        """Test that asyncio synchronization primitives work with decorated functions"""

        semaphore = asyncio.Semaphore(2)
        lock = asyncio.Lock()
        shared_resource = []

        @instrument
        async def semaphore_task(task_id):
            async with semaphore:
                await asyncio.sleep(0.01)
                return f"task_{task_id}_completed"

        @instrument
        async def lock_task(task_id):
            async with lock:
                shared_resource.append(task_id)
                await asyncio.sleep(0.01)
                return len(shared_resource)

        # Test semaphore
        sem_results = await asyncio.gather(*[semaphore_task(i) for i in range(5)])
        assert len(sem_results) == 5
        assert all("completed" in result for result in sem_results)

        # Test lock
        lock_results = await asyncio.gather(*[lock_task(i) for i in range(3)])
        # Due to lock, each task should see sequential lengths
        assert sorted(lock_results) == [1, 2, 3]
        assert len(shared_resource) == 3

    async def test_condition_variable(self):
        """Test that asyncio.Condition works with decorated functions"""

        condition = asyncio.Condition()
        results = []

        @instrument
        async def waiter(waiter_id):
            async with condition:
                await condition.wait()
                results.append(f"waiter_{waiter_id}_notified")
                return waiter_id

        @instrument
        async def notifier():
            await asyncio.sleep(0.01)  # Let waiters start
            async with condition:
                condition.notify_all()
            return "notified_all"

        # Start waiters and notifier
        waiter_tasks = [asyncio.create_task(waiter(i)) for i in range(3)]
        notifier_task = asyncio.create_task(notifier())

        # Wait for all to complete
        all_results = await asyncio.gather(*waiter_tasks, notifier_task)

        assert "notified_all" in all_results
        assert len(results) == 3
        assert all("notified" in result for result in results)

    async def test_event_coordination(self):
        """Test that asyncio.Event works with decorated functions"""

        event = asyncio.Event()
        coordination_results = []

        @instrument
        async def waiter(waiter_id):
            await event.wait()
            coordination_results.append(waiter_id)
            return f"waiter_{waiter_id}"

        @instrument
        async def setter():
            await asyncio.sleep(0.01)
            event.set()
            return "event_set"

        # Start multiple waiters
        waiter_tasks = [asyncio.create_task(waiter(i)) for i in range(3)]
        setter_task = asyncio.create_task(setter())

        results = await asyncio.gather(*waiter_tasks, setter_task)

        assert "event_set" in results
        assert len(coordination_results) == 3
        assert sorted(coordination_results) == [0, 1, 2]

    async def test_queue_operations(self):
        """Test that asyncio.Queue works with decorated functions"""

        queue = asyncio.Queue(maxsize=2)

        @instrument
        async def producer(items):
            for item in items:
                await queue.put(item)
                await asyncio.sleep(0.001)
            return f"produced_{len(items)}_items"

        @instrument
        async def consumer(expected_count):
            consumed = []
            for _ in range(expected_count):
                item = await queue.get()
                consumed.append(item)
                queue.task_done()
            return consumed

        # Test producer/consumer pattern
        producer_task = asyncio.create_task(producer([1, 2, 3, 4]))
        consumer_task = asyncio.create_task(consumer(4))

        producer_result, consumer_result = await asyncio.gather(producer_task, consumer_task)

        assert producer_result == "produced_4_items"
        assert consumer_result == [1, 2, 3, 4]

    async def test_timeout_behavior(self):
        """Test that asyncio.timeout works correctly with decorated functions"""

        @instrument
        async def slow_task():
            await asyncio.sleep(0.1)
            return "completed"

        @instrument
        async def fast_task():
            await asyncio.sleep(0.01)
            return "completed"

        # Test timeout with slow task
        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.05):
                await slow_task()

        # Test no timeout with fast task
        async with asyncio.timeout(0.05):
            result = await fast_task()
        assert result == "completed"

    async def test_wait_for_behavior(self):
        """Test that asyncio.wait_for works correctly with decorated functions"""

        @instrument
        async def slow_task():
            await asyncio.sleep(0.1)
            return "slow_completed"

        @instrument
        async def fast_task():
            await asyncio.sleep(0.01)
            return "fast_completed"

        # Test timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_task(), timeout=0.05)

        # Test no timeout
        result = await asyncio.wait_for(fast_task(), timeout=0.05)
        assert result == "fast_completed"

    async def test_as_completed_behavior(self):
        """Test that asyncio.as_completed works with decorated functions"""

        @instrument
        async def task_with_delay(delay, value):
            await asyncio.sleep(delay)
            return value

        tasks = [
            task_with_delay(0.03, "third"),
            task_with_delay(0.01, "first"),
            task_with_delay(0.02, "second"),
        ]

        results = []
        for completed_task in asyncio.as_completed(tasks):
            result = await completed_task
            results.append(result)

        # Should complete in order of delay (fastest first)
        assert results == ["first", "second", "third"]

    async def test_shield_edge_cases(self):
        """Test edge cases with asyncio.shield"""

        @instrument
        async def shielded_task():
            await asyncio.sleep(0.05)
            return "shielded_completed"

        @instrument
        async def outer_task():
            try:
                # This should timeout but not cancel the shielded task
                result = await asyncio.wait_for(asyncio.shield(shielded_task()), timeout=0.02)
                return result
            except asyncio.TimeoutError:
                # Give the shielded task time to complete
                await asyncio.sleep(0.1)
                return "timeout_handled"

        result = await outer_task()
        assert result == "timeout_handled"

    async def test_nested_decorators_with_asyncio_features(self):
        """Test complex nested scenarios with various asyncio features"""

        @instrument
        async def inner_task(value):
            await asyncio.sleep(0.01)
            return value * 2

        @instrument
        async def middle_task(values):
            # Use gather inside decorated function
            results = await asyncio.gather(*[inner_task(v) for v in values])
            return sum(results)

        @instrument
        async def outer_task():
            # Use multiple asyncio features together
            async with asyncio.timeout(1.0):
                result1 = await middle_task([1, 2, 3])
                result2 = await asyncio.wait_for(middle_task([4, 5]), timeout=0.1)
                return result1 + result2

        result = await outer_task()
        # (1*2 + 2*2 + 3*2) + (4*2 + 5*2) = 12 + 18 = 30
        assert result == 30
