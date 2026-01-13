#!/usr/bin/env python3
"""
Demo script showing sync and async generator instrumentation with Jot.

This script demonstrates how the @jot.instrument decorator works with:
1. Sync generators
2. Async generators
3. Error handling in generators
4. Tag propagation
"""

import asyncio

import jot
from jot import facade
from jot.base import Target


class DemoTarget(Target):
    """A simple target that prints telemetry to stdout"""

    def log(self, level, message, tags, span=None):
        span_info = f"[{span.name}:{span.id[:8]}]" if span else "[no-span]"
        print(f"LOG {span_info} {message} {tags}")

    def error(self, message, exception, tags, span=None):
        span_info = f"[{span.name}:{span.id[:8]}]" if span else "[no-span]"
        print(f"ERROR {span_info} {message}: {exception} {tags}")

    def finish(self, tags, span):
        print(f"FINISH [{span.name}:{span.id[:8]}] duration={span.duration / 1000000:.2f}ms {tags}")


def setup_jot():
    """Initialize jot with demo target"""
    target = DemoTarget()
    jot.init(target)

    # Create root span
    root = jot.span("demo-root")
    facade._swap_active(root)
    root.start()
    return root


@jot.instrument("user_id")
def sync_fibonacci_generator(n, user_id=None):
    """Generate fibonacci numbers up to n with instrumentation"""
    jot.info("starting fibonacci generation", n=n)

    a, b = 0, 1
    count = 0

    while count < n:
        jot.info("yielding fibonacci number", value=a, position=count)
        yield a
        a, b = b, a + b
        count += 1

    jot.info("fibonacci generation complete", total_generated=count)


@jot.instrument(service="data-processor")
async def async_data_processor(items):
    """Process items asynchronously with instrumentation"""
    jot.info("starting async data processing", item_count=len(items))

    for i, item in enumerate(items):
        jot.info("processing item", item=item, index=i)

        # Simulate async processing
        await asyncio.sleep(0.1)

        # Process and yield result
        result = f"processed_{item}"
        jot.info("yielding processed result", result=result)
        yield result

    jot.info("async data processing complete")


@jot.instrument
def error_prone_generator():
    """Generator that demonstrates error handling"""
    jot.info("starting error-prone generation")

    yield "first_value"
    jot.info("yielded first value successfully")

    yield "second_value"
    jot.info("yielded second value successfully")

    # This will cause an error
    raise ValueError("Something went wrong!")
    yield "unreachable_value"


@jot.instrument
async def async_error_generator():
    """Async generator that demonstrates error handling"""
    jot.info("starting async error generation")

    await asyncio.sleep(0.05)
    yield "async_first"
    jot.info("yielded async first value")

    await asyncio.sleep(0.05)
    raise RuntimeError("Async error occurred!")
    yield "async_unreachable"


def demo_sync_generator():
    """Demonstrate sync generator instrumentation"""
    print("\n=== SYNC GENERATOR DEMO ===")

    # Create generator
    fib_gen = sync_fibonacci_generator(5, user_id="user123")

    print("Generator created, consuming values...")
    for value in fib_gen:
        print(f"Got fibonacci: {value}")

    print("Sync generator demo complete!")


async def demo_async_generator():
    """Demonstrate async generator instrumentation"""
    print("\n=== ASYNC GENERATOR DEMO ===")

    # Create async generator
    items = ["apple", "banana", "cherry"]
    processor = async_data_processor(items)

    print("Async generator created, consuming values...")
    async for result in processor:
        print(f"Got processed: {result}")

    print("Async generator demo complete!")


def demo_sync_error_handling():
    """Demonstrate error handling in sync generators"""
    print("\n=== SYNC ERROR HANDLING DEMO ===")

    gen = error_prone_generator()

    try:
        print(f"First value: {next(gen)}")
        print(f"Second value: {next(gen)}")
        print(f"Third value: {next(gen)}")  # This will cause error
    except ValueError as e:
        print(f"Caught expected error: {e}")

    print("Sync error handling demo complete!")


async def demo_async_error_handling():
    """Demonstrate error handling in async generators"""
    print("\n=== ASYNC ERROR HANDLING DEMO ===")

    agen = async_error_generator()

    try:
        print(f"First async value: {await agen.__anext__()}")
        print(f"Second async value: {await agen.__anext__()}")  # This will cause error
    except RuntimeError as e:
        print(f"Caught expected async error: {e}")

    print("Async error handling demo complete!")


def demo_generator_methods():
    """Demonstrate generator methods (send, throw, close)"""
    print("\n=== GENERATOR METHODS DEMO ===")

    @jot.instrument
    def interactive_generator():
        jot.info("generator started")

        value = yield "ready"
        jot.info("received value via send", received=value)

        try:
            yield f"echo: {value}"
        except Exception as e:
            jot.info("caught exception", exception_type=type(e).__name__)
            yield "recovered"

        jot.info("generator ending")

    gen = interactive_generator()

    # Start generator
    print(f"Initial: {next(gen)}")

    # Send value
    print(f"Send result: {gen.send('hello')}")

    # Close generator
    gen.close()
    print("Generator closed")


async def demo_async_generator_methods():
    """Demonstrate async generator methods"""
    print("\n=== ASYNC GENERATOR METHODS DEMO ===")

    @jot.instrument
    async def async_interactive_generator():
        jot.info("async generator started")

        value = yield "async_ready"
        jot.info("received async value", received=value)

        await asyncio.sleep(0.01)
        yield f"async_echo: {value}"

        jot.info("async generator ending")

    agen = async_interactive_generator()

    # Start async generator
    print(f"Async initial: {await agen.__anext__()}")

    # Send value to async generator
    print(f"Async send result: {await agen.asend('async_hello')}")

    # Close async generator
    await agen.aclose()
    print("Async generator closed")


async def main():
    """Run all generator demos"""
    print("🚀 Jot Generator Instrumentation Demo")
    print("=" * 50)

    # Setup
    root = setup_jot()

    try:
        # Run demos
        demo_sync_generator()
        await demo_async_generator()
        demo_sync_error_handling()
        await demo_async_error_handling()
        demo_generator_methods()
        await demo_async_generator_methods()

        print("\n✅ All demos completed successfully!")

    finally:
        # Cleanup
        root.finish()


if __name__ == "__main__":
    asyncio.run(main())
