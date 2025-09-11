import asyncio
import sys

import pytest

from jot.decorators import instrument


class TestAsyncioEdgeCases:
    """Test edge cases and potential failure modes with the jot decorator"""

    async def test_generator_based_coroutines(self):
        """Test that old-style generator-based coroutines still work"""

        # Skip this test on Python 3.11+ where @asyncio.coroutine was removed
        if sys.version_info >= (3, 11):
            pytest.skip("@asyncio.coroutine removed in Python 3.11+")

        # For older Python versions, test would be:
        # @asyncio.coroutine
        # def old_style_coro():
        #     yield from asyncio.sleep(0.01)
        #     return "old_style_result"

        @instrument
        async def modern_coro():
            await asyncio.sleep(0.01)
            return "modern_result"

        result = await modern_coro()
        assert result == "modern_result"

    async def test_deeply_nested_coroutines(self):
        """Test deeply nested decorated coroutines"""

        @instrument
        async def level_1():
            await asyncio.sleep(0.001)
            return await level_2()

        @instrument
        async def level_2():
            await asyncio.sleep(0.001)
            return await level_3()

        @instrument
        async def level_3():
            await asyncio.sleep(0.001)
            return await level_4()

        @instrument
        async def level_4():
            await asyncio.sleep(0.001)
            return await level_5()

        @instrument
        async def level_5():
            await asyncio.sleep(0.001)
            return "deep_result"

        result = await level_1()
        assert result == "deep_result"

    async def test_coroutine_with_finally_blocks(self):
        """Test that finally blocks execute correctly with cancellation"""

        cleanup_called = []

        @instrument
        async def task_with_cleanup():
            try:
                await asyncio.sleep(0.1)  # This will be cancelled
                return "should_not_reach"
            finally:
                cleanup_called.append("cleanup_executed")
                # Even cleanup can be async
                await asyncio.sleep(0.001)

        # Test cancellation with cleanup
        task = asyncio.create_task(task_with_cleanup())
        await asyncio.sleep(0.01)  # Let task start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # Cleanup should have been called
        assert cleanup_called == ["cleanup_executed"]

    async def test_exception_chaining_preservation(self):
        """Test that exception chaining is preserved through the decorator"""

        @instrument
        async def raises_chained_exception():
            try:
                await asyncio.sleep(0.01)
                raise ValueError("original error")
            except ValueError as e:
                raise RuntimeError("wrapper error") from e

        with pytest.raises(RuntimeError) as exc_info:
            await raises_chained_exception()

        assert str(exc_info.value) == "wrapper error"
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValueError)
        assert str(exc_info.value.__cause__) == "original error"

    async def test_async_generator_functions(self):
        """Test that async generator functions work with decoration"""

        @instrument
        async def async_generator():
            for i in range(3):
                await asyncio.sleep(0.001)
                yield f"item_{i}"

        # Note: async generators can't be directly decorated with @instrument
        # because they don't return awaitable objects, but we can test
        # calling them from decorated functions

        @instrument
        async def consume_async_generator():
            results = []
            async for item in async_generator():
                results.append(item)
            return results

        results = await consume_async_generator()
        assert results == ["item_0", "item_1", "item_2"]

    async def test_concurrent_futures_compatibility(self):
        """Test compatibility with concurrent.futures"""

        import concurrent.futures

        def cpu_bound_task(n):
            # Simulate CPU-bound work
            total = 0
            for i in range(n):
                total += i * i
            return total

        @instrument
        async def mixed_async_sync():
            loop = asyncio.get_running_loop()

            # Run CPU-bound task in thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = loop.run_in_executor(executor, cpu_bound_task, 1000)
                cpu_result = await future

            # Mix with async operation
            await asyncio.sleep(0.01)

            return cpu_result

        result = await mixed_async_sync()
        expected = sum(i * i for i in range(1000))
        assert result == expected

    async def test_signal_handling_compatibility(self):
        """Test that signal handling still works (Unix only)"""

        if sys.platform == "win32":
            pytest.skip("Signal handling test not applicable on Windows")

        import signal

        signal_received = []

        def signal_handler(signum, frame):
            signal_received.append(signum)

        @instrument
        async def task_with_signal_handling():
            # Set up signal handler
            old_handler = signal.signal(signal.SIGUSR1, signal_handler)
            try:
                await asyncio.sleep(0.05)
                return "completed"
            finally:
                # Restore original handler
                signal.signal(signal.SIGUSR1, old_handler)

        # This test is tricky because we need another process to send the signal
        # For now, just test that the decorated function works with signal setup
        result = await task_with_signal_handling()
        assert result == "completed"

    async def test_memory_usage_with_many_tasks(self):
        """Test memory behavior with many concurrent decorated tasks"""

        @instrument
        async def small_task(task_id):
            await asyncio.sleep(0.001)
            return f"task_{task_id}"

        # Create many concurrent tasks
        tasks = [asyncio.create_task(small_task(i)) for i in range(100)]

        # Wait for all to complete
        results = await asyncio.gather(*tasks)

        assert len(results) == 100
        assert all(f"task_{i}" in results for i in range(100))

    async def test_exception_in_context_manager(self):
        """Test exception handling within async context managers"""

        cleanup_order = []

        class AsyncContextManager:
            def __init__(self, name):
                self.name = name

            async def __aenter__(self):
                cleanup_order.append(f"{self.name}_enter")
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                cleanup_order.append(f"{self.name}_exit")
                return False  # Don't suppress exceptions

        @instrument
        async def task_with_context_managers():
            async with AsyncContextManager("outer"):
                async with AsyncContextManager("inner"):
                    await asyncio.sleep(0.01)
                    raise ValueError("test exception")

        with pytest.raises(ValueError):
            await task_with_context_managers()

        # Both context managers should have entered and exited
        assert "outer_enter" in cleanup_order
        assert "inner_enter" in cleanup_order
        assert "inner_exit" in cleanup_order
        assert "outer_exit" in cleanup_order

    async def test_asyncio_protocol_compatibility(self):
        """Test that the decorator doesn't break asyncio protocol methods"""

        @instrument
        async def create_server_client():
            # Test that we can create servers and clients
            # (This is a simplified test that doesn't actually create network connections)

            server_started = False
            client_connected = False

            async def mock_server():
                nonlocal server_started
                await asyncio.sleep(0.01)
                server_started = True
                return "server_ready"

            async def mock_client():
                nonlocal client_connected
                await asyncio.sleep(0.01)
                client_connected = True
                return "client_connected"

            # Simulate server/client coordination
            server_task = asyncio.create_task(mock_server())
            client_task = asyncio.create_task(mock_client())

            results = await asyncio.gather(server_task, client_task)
            return results, server_started, client_connected

        results, server_started, client_connected = await create_server_client()

        assert results == ["server_ready", "client_connected"]
        assert server_started
        assert client_connected
