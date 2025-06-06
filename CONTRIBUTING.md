# Contributing to Pyjot

This guide is for developers who want to hack on Pyjot itself.

## Architecture Overview

Pyjot uses a simple facade pattern:

```
jot.* functions → facade.py → active_meter → target.method()
```

### Core Components

**`facade.py`** - Global API entry points (`jot.info()`, `jot.count()`, etc.)
**`base.py`** - `Meter` class that handles spans and delegates to targets
**`decorators.py`** - `@instrument` decorator for function tracing
**Target classes** - Handle actual telemetry delivery

### Key Classes

**`Meter`** - Instrumentation context with active span and tags
**`Span`** - Represents a trace segment with timing and metadata  
**`Target`** - Base class for telemetry destinations
**`*Target`** - Concrete implementations (Print, OTLP, Sentry, etc.)

## Development Setup

```bash
git clone https://github.com/vannevar-labs/pyjot
cd pyjot
pip install -e .[dev]
pre-commit install
```

## Testing

```bash
# All tests
pytest

# Specific target
pytest tests/test_sentry.py

# Skip integration tests
pytest -m "not integration"
```

### Test Structure

- `tests/test_*.py` - Unit tests for each module
- `scenarios/` - Integration test scenarios
- Mocks external services (Sentry, Rollbar, etc.)

## Adding a New Target

1. Create `jot/{name}.py`
2. Inherit from `Target` base class
3. Implement required methods:
   - `log(level, message, tags, span)`
   - `error(message, exception, tags, span)`
   - `magnitude(name, value, tags, span)`
   - `count(name, value, tags, span)`
   - `start(tags, span)` / `finish(tags, span)` (optional)

Example skeleton:

```python
from .base import Target
from . import log

class MyTarget(Target):
    def __init__(self, endpoint, level=log.DEFAULT):
        super().__init__(level)
        self.endpoint = endpoint
    
    def log(self, level, message, tags, span=None):
        if not self.accepts_log_level(level):
            return
        # Send log to external service
        
    def error(self, message, exception, tags, span=None):
        # Send error with stack trace
        
    def magnitude(self, name, value, tags, span=None):
        # Send point-in-time metric
        
    def count(self, name, value, tags, span=None):
        # Send cumulative metric
```

4. Add tests in `tests/test_{name}.py`
5. Add to `pyproject.toml` optional dependencies if needed

## Code Style

- Use `ruff` for linting (configured in `ruff.toml`)
- Follow existing patterns in the codebase
- Keep interfaces minimal and consistent
- Error handling should be defensive - don't break user code

## Key Design Principles

**No-op by default** - If `jot.init()` is never called, all operations are no-ops
**Fail gracefully** - Target errors shouldn't crash user applications
**Minimal overhead** - Fast path for when telemetry is disabled
**Composable** - Targets can be combined with `FanOutTarget`

## Testing Targets

Most targets need external services. Use environment variables to enable:

```bash
# Postgres tests
export POSTGRES_HOST=localhost POSTGRES_DB=test
pytest tests/test_pg.py

# Sentry tests  
export SENTRY_DSN=https://...
pytest tests/test_sentry.py
```

Tests are skipped if required environment isn't available.

## Common Patterns

### Error Handling in Targets
```python
def log(self, level, message, tags, span=None):
    try:
        # ... send telemetry
    except Exception:
        # Log but don't re-raise - telemetry failures 
        # shouldn't break user code
        pass
```

### Tag Merging
```python
# Combine meter tags with call-specific tags
combined_tags = {**self.tags, **call_tags}
```

### Span Context
```python
def log(self, level, message, tags, span=None):
    if span:
        tags.update({
            "trace_id": span.trace_id,
            "span_id": span.id
        })
```

## Release Process

1. Update version in `pyproject.toml`
2. Tag release: `git tag v0.1.x`
3. Push: `git push origin v0.1.x`
4. GitHub Actions builds and publishes to PyPI

## Questions?

Open an issue or reach out to maintainers.