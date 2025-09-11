import asyncio

import pytest

from jot.decorators import instrument


class TestStructuredConcurrency:
    """Test structured concurrency patterns with the jot decorator"""

    async def test_anyio_style_nursery_pattern(self):
        """Test a manual implementation of nursery-style structured concurrency"""

        @instrument
        async def worker_task(worker_id, delay):
            await asyncio.sleep(delay)
            if worker_id == 3:
                raise ValueError(f"Worker {worker_id} failed")
            return f"worker_{worker_id}_done"

        @instrument
        async def nursery_coordinator():
            """Manual nursery-like pattern"""
            tasks = []
            try:
                # Start multiple tasks
                for i in range(5):
                    task = asyncio.create_task(worker_task(i, 0.01 * (i + 1)))
                    tasks.append(task)

                # Wait for all tasks
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return results
            except Exception:
                # Cancel all remaining tasks on exception
                for task in tasks:
                    task.cancel()
                raise

        results = await nursery_coordinator()

        # Should have 4 successful results and 1 exception
        successful = [r for r in results if isinstance(r, str)]
        exceptions = [r for r in results if isinstance(r, Exception)]

        assert len(successful) == 4
        assert len(exceptions) == 1
        assert isinstance(exceptions[0], ValueError)
        assert "Worker 3 failed" in str(exceptions[0])

    async def test_supervisor_pattern(self):
        """Test supervisor-style error handling with decorated functions"""

        restart_count = 0

        @instrument
        async def unreliable_service():
            nonlocal restart_count
            restart_count += 1
            await asyncio.sleep(0.01)
            if restart_count < 3:
                raise ConnectionError(f"Service failed (attempt {restart_count})")
            return f"Service succeeded after {restart_count} attempts"

        @instrument
        async def supervisor(max_retries=3):
            """Supervisor that restarts failed services"""
            for attempt in range(max_retries):
                try:
                    result = await unreliable_service()
                    return result
                except ConnectionError:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(0.01)  # Brief delay before retry

        result = await supervisor()
        assert result == "Service succeeded after 3 attempts"
        assert restart_count == 3

    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern with decorated functions"""

        failure_count = 0

        @instrument
        async def failing_external_service():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise ConnectionError("External service down")
            return "External service response"

        @instrument
        async def circuit_breaker(func, failure_threshold=3):
            """Simple circuit breaker implementation"""
            failures = 0
            circuit_open = False

            async def protected_call():
                nonlocal failures, circuit_open

                if circuit_open:
                    raise RuntimeError("Circuit breaker is OPEN")

                try:
                    result = await func()
                    failures = 0  # Reset on success
                    return result
                except Exception:
                    failures += 1
                    if failures >= failure_threshold:
                        circuit_open = True
                    raise

            return protected_call

        protected_service = await circuit_breaker(failing_external_service)

        # First 3 calls should fail with connection error
        for i in range(3):
            with pytest.raises(ConnectionError):
                await protected_service()

        # 4th call should fail with circuit breaker open
        with pytest.raises(RuntimeError, match="Circuit breaker is OPEN"):
            await protected_service()

    async def test_pipeline_pattern(self):
        """Test pipeline/chain pattern with decorated functions"""

        @instrument
        async def stage1_input(data):
            await asyncio.sleep(0.01)
            return [x * 2 for x in data]

        @instrument
        async def stage2_transform(data):
            await asyncio.sleep(0.01)
            return [x + 10 for x in data]

        @instrument
        async def stage3_filter(data):
            await asyncio.sleep(0.01)
            return [x for x in data if x > 15]

        @instrument
        async def stage4_output(data):
            await asyncio.sleep(0.01)
            return sum(data)

        @instrument
        async def pipeline_processor(input_data):
            """Process data through multiple stages"""
            result = input_data
            result = await stage1_input(result)
            result = await stage2_transform(result)
            result = await stage3_filter(result)
            result = await stage4_output(result)
            return result

        # Input: [1, 2, 3, 4, 5]
        # Stage 1: [2, 4, 6, 8, 10] (multiply by 2)
        # Stage 2: [12, 14, 16, 18, 20] (add 10)
        # Stage 3: [16, 18, 20] (filter > 15)
        # Stage 4: 54 (sum)

        result = await pipeline_processor([1, 2, 3, 4, 5])
        assert result == 54

    async def test_fan_out_fan_in_pattern(self):
        """Test fan-out/fan-in pattern with decorated functions"""

        @instrument
        async def worker_process(item, multiplier):
            await asyncio.sleep(0.01)
            return item * multiplier

        @instrument
        async def aggregator(results):
            await asyncio.sleep(0.01)
            return sum(results)

        @instrument
        async def fan_out_fan_in_processor(input_data):
            """Fan out to multiple workers, then fan in to aggregator"""
            # Fan out: process each item with different multipliers
            worker_tasks = []
            for i, item in enumerate(input_data):
                multiplier = i + 2  # Different multiplier for each worker
                task = asyncio.create_task(worker_process(item, multiplier))
                worker_tasks.append(task)

            # Wait for all workers to complete
            worker_results = await asyncio.gather(*worker_tasks)

            # Fan in: aggregate results
            final_result = await aggregator(worker_results)
            return final_result

        # Input: [1, 2, 3]
        # Worker 0: 1 * 2 = 2
        # Worker 1: 2 * 3 = 6
        # Worker 2: 3 * 4 = 12
        # Aggregate: 2 + 6 + 12 = 20

        result = await fan_out_fan_in_processor([1, 2, 3])
        assert result == 20

    async def test_resource_pool_pattern(self):
        """Test resource pool pattern with decorated functions"""

        # Simulate a resource pool with semaphore
        resource_pool = asyncio.Semaphore(2)  # Max 2 concurrent resources
        active_resources = []

        @instrument
        async def acquire_resource(resource_id):
            async with resource_pool:
                active_resources.append(resource_id)
                await asyncio.sleep(0.02)  # Simulate resource usage
                active_resources.remove(resource_id)
                return f"resource_{resource_id}_used"

        @instrument
        async def resource_manager():
            """Manage multiple resource requests"""
            tasks = []
            for i in range(5):
                task = asyncio.create_task(acquire_resource(i))
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            return results

        results = await resource_manager()

        assert len(results) == 5
        assert all("resource_" in result and "_used" in result for result in results)
        assert len(active_resources) == 0  # All resources should be released
