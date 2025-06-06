# Pyjot

A lightweight Python library for telemetry instrumentation - logs, metrics, traces, and errors.

## Quick Start

```python
import jot
from jot.print import PrintTarget

# Initialize with a target and global tags
jot.init(PrintTarget(), {"service": "my-app", "environment": "production"})

# Structured logging
jot.info("User logged in", {"user_id": 123, "method": "oauth"})

# Metrics
jot.count("requests", 1, {"endpoint": "/api/users", "status": 200})
jot.magnitude("memory_usage_mb", 256, {"process": "worker"})

# Error tracking with stack traces
try:
    result = 1 / 0
except ZeroDivisionError as e:
    jot.error("Division error", e, {"operation": "calculate"})

# Function tracing
@jot.instrument
def process_order(order_id):
    jot.info("Processing order", {"order_id": order_id})
    return "processed"

process_order(456)  # Automatically creates a trace span
```

## Key Features

- **Zero-config telemetry** - If `jot.init()` is never called, all operations are no-ops
- **Structured everything** - Logs, metrics, errors, and traces all support key-value tags
- **Multiple targets** - Send to console, OpenTelemetry, Sentry, Rollbar, or multiple destinations
- **Automatic tracing** - `@jot.instrument` decorator for effortless function tracing
- **Python logging bridge** - Route standard library logging through Jot targets

## Targets

Send telemetry to different destinations:

- **PrintTarget** - Console output for development
- **OTLPTarget** - OpenTelemetry for production observability  
- **SentryTarget** - Error tracking and performance monitoring
- **RollbarTarget** - Error reporting
- **FanOutTarget** - Send to multiple targets simultaneously

## Installation

```bash
pip install dl-jot

# With optional dependencies
pip install dl-jot[sentry,rollbar,postgres,otel]
```

## Documentation

- **[Quick Reference](QUICKREF.md)** - Common patterns and examples
- **[API Reference](API.md)** - Complete function and class documentation  
- **[Contributing Guide](CONTRIBUTING.md)** - For developers working on Pyjot itself

## License

See LICENSE file.