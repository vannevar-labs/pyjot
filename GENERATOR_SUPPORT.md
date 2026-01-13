# Generator Support in Jot

This document describes the support for instrumenting Python generators and async generators using the `@jot.instrument` decorator.

## Overview

As of this implementation, the `@jot.instrument` decorator now supports:

- ✅ Synchronous functions
- ✅ Asynchronous functions (coroutines)
- ✅ **Synchronous generators** (NEW)
- ✅ **Asynchronous generators** (NEW)

## How Generator Instrumentation Works

### Span Lifecycle for Generators

Unlike regular functions where the span covers a single execution, generators have a different lifecycle:

1. **Span Creation**: The span is created when the generator is first iterated (first `next()` or `__anext__()` call)
2. **Span Context**: The span remains active during each yield/iteration cycle
3. **Span Completion**: The span finishes when the generator is exhausted, closed, or encounters an error

### Synchronous Generators

```python
import jot

@jot.instrument("user_id")
def fibonacci_generator(n, user_id=None):
    """Generate fibonacci numbers with instrumentation"""
    jot.info("starting fibonacci generation", n=n)
    
    a, b = 0, 1
    count = 0
    
    while count < n:
        jot.info("yielding number", value=a, position=count)
        yield a
        a, b = b, a + b
        count += 1
    
    jot.info("generation complete", total=count)

# Usage
for value in fibonacci_generator(5, user_id="user123"):
    print(f"Got: {value}")
```

**Key Features:**
- Span is created on first `next()` call
- Span context is active during each yield
- Supports all generator methods: `send()`, `throw()`, `close()`
- Proper error handling and span completion

### Asynchronous Generators

```python
import asyncio
import jot

@jot.instrument(service="data-processor")
async def process_items(items):
    """Process items asynchronously with instrumentation"""
    jot.info("starting processing", item_count=len(items))
    
    for i, item in enumerate(items):
        jot.info("processing item", item=item, index=i)
        
        # Simulate async work
        await asyncio.sleep(0.1)
        
        result = f"processed_{item}"
        jot.info("yielding result", result=result)
        yield result
    
    jot.info("processing complete")

# Usage
async def main():
    items = ["apple", "banana", "cherry"]
    async for result in process_items(items):
        print(f"Got: {result}")

asyncio.run(main())
```

**Key Features:**
- Span is created on first `__anext__()` call
- Supports async/await within the generator
- Supports async generator methods: `asend()`, `athrow()`, `aclose()`
- Proper async error handling

## Error Handling

Both sync and async generators properly handle errors:

```python
@jot.instrument
def error_generator():
    yield "first"
    yield "second"
    raise ValueError("Something went wrong!")
    yield "unreachable"

# The error will be logged and the span will finish
gen = error_generator()
print(next(gen))  # "first"
print(next(gen))  # "second"
print(next(gen))  # Raises ValueError, error is logged to span
```

## Tag Support

Generators support both static and dynamic tags just like regular functions:

```python
# Static tags
@jot.instrument(service="my-service", version="1.0")
def tagged_generator():
    yield "value"

# Dynamic tags
@jot.instrument("user_id", "session_id")
def dynamic_tagged_generator(user_id=None, session_id=None):
    yield "value"

# Usage with dynamic tags
for value in dynamic_tagged_generator(user_id="user123", session_id="sess456"):
    print(value)
```

## Generator Methods

All standard generator methods are supported:

### Sync Generator Methods

```python
gen = my_sync_generator()

# Standard iteration
value = next(gen)

# Send values
result = gen.send(some_value)

# Throw exceptions
try:
    gen.throw(ValueError, "test error")
except StopIteration:
    pass

# Close generator
gen.close()
```

### Async Generator Methods

```python
agen = my_async_generator()

# Standard async iteration
value = await agen.__anext__()

# Send values asynchronously
result = await agen.asend(some_value)

# Throw exceptions asynchronously
try:
    await agen.athrow(ValueError, "test error")
except StopAsyncIteration:
    pass

# Close async generator
await agen.aclose()
```

## Implementation Details

### Detection

The decorator automatically detects generator types using Python's `inspect` module:

- `inspect.isgeneratorfunction()` for sync generators
- `inspect.isasyncgenfunction()` for async generators

### Wrapper Classes

Generators are wrapped with special instrumentation classes:

- `InstrumentedSyncGenerator` for sync generators
- `InstrumentedAsyncGenerator` for async generators

These classes implement the full generator protocol while managing span lifecycle.

### Span Context Management

The implementation carefully manages span context:

1. **Activation**: Span becomes active before each generator operation
2. **Deactivation**: Parent span is restored after each operation
3. **Cleanup**: Span is properly finished when generator completes

## Testing

Comprehensive tests are included covering:

- Basic generator iteration
- Tag propagation (static and dynamic)
- Error handling and reporting
- Generator method support (`send`, `throw`, `close`, etc.)
- Async generator functionality
- Span lifecycle management

Run generator-specific tests with:

```bash
pytest tests/test_instrument.py::test_sync_generator
pytest tests/test_instrument.py::test_async_generator
pytest tests/test_instrument.py::test_sync_generator_tag_one
pytest tests/test_instrument.py::test_async_generator_tag_one
pytest tests/test_instrument.py::test_sync_generator_throws
pytest tests/test_instrument.py::test_async_generator_throws
```

## Demo

See `demo_generators.py` for a comprehensive demonstration of all generator instrumentation features.

## Limitations

- Generator detection only works on the original function before decoration
- Once decorated, the function type is no longer detectable as a generator
- Test framework integration required special handling for async generators

## Future Enhancements

Potential future improvements:

- Support for generator expressions
- Performance optimizations for high-frequency generators
- Additional generator-specific metrics
- Integration with context managers