# Pyjot API Reference

Complete reference for all public functions and classes in Pyjot.

## Core Functions

### `jot.init(target, **tags)`

Initialize Pyjot with a telemetry target and optional global tags.

**Parameters:**
- `target` - Target instance that handles telemetry delivery
- `**tags` - Key-value pairs added to all telemetry

**Example:**
```python
jot.init(PrintTarget(), service='api', version='1.0')
```

### Logging Functions

#### `jot.debug(message, **tags)`
#### `jot.info(message, **tags)`
#### `jot.warning(message, **tags)`

Send structured log messages.

**Parameters:**
- `message` (str) - Log message
- `tags` (kwargs, optional) - Additional metadata

**Example:**
```python
jot.info('User authenticated', user_id=123, method='oauth')
```

### Metrics Functions

#### `jot.count(name, value, **tags)`

Record cumulative metrics (requests, errors, events).

**Parameters:**
- `name` (str) - Metric name
- `value` (int/float) - Amount to add
- `tags` (kwargs, optional) - Metric dimensions

**Example:**
```python
jot.count('api.requests', 1, endpoint='/users', status=200)
```

#### `jot.magnitude(name, value, **tags)`

Record point-in-time measurements (memory, CPU, queue depth).

**Parameters:**
- `name` (str) - Metric name
- `value` (int/float) - Current measurement
- `tags` (kwargs, optional) - Metric dimensions

**Example:**
```python
jot.magnitude('memory.usage_mb', 512, process='worker'})
```

### Error Tracking

#### `jot.error(message, exception, **tags)`

Report errors with stack traces.

**Parameters:**
- `message` (str) - Error description
- `exception` (Exception) - Python exception object
- `tags` (kwargs, optional) - Error context

**Example:**
```python
try:
    risky_operation()
except ValueError as e:
    jot.error('Invalid input data', e, input_type='json'})
```

### Tracing Functions

#### `jot.span(name, **tags)`

Create a trace span context manager.

**Parameters:**
- `name` (str) - Span name
- `trace_id` (str, optional) - Specific trace ID
- `parent_id` (str, optional) - Parent span ID
- `**tags` - Additional span tags

**Returns:** Context manager for the span

**Example:**
```python
with jot.span('database_query', table='users'):
    result = db.execute('SELECT * FROM users')
```

#### `jot.start(name=None, **tags)`

Start a new span or the current active span.

**Parameters:**
- `name` (str, optional) - New span name, creates child span
- `**tags` - Span tags

**Returns:** Meter instance for the started span

#### `jot.finish(**tags)`

Finish the current active span.

**Parameters:**
- `*tags` - Additional tags to add when finishing

#### `jot.generate_trace_id()`

Generate a new trace ID.

**Returns:** String trace ID

### Events

#### `jot.event(name, **tags)`

Record structured events.

**Parameters:**
- `name` (str) - Event name
- `tags` (kwargs, optional) - Event data

**Example:**
```python
jot.event('user.signup', source='landing_page', plan='premium'})
```

## Decorators

### `@jot.instrument`
### `@jot.instrument(tag_name='value')`
### `@jot.instrument('tag_name')`

Decorator to automatically trace function calls.

**Variants:**
- `@jot.instrument` - Creates span with function name
- `@jot.instrument(category='db')` - Adds category tag to all telemetry in function
- `@jot.instrument('user_id')` - Extracts `user_id` kwarg for span tags (not passed to function)

**Example:**
```python
@jot.instrument
def fetch_user(user_id):
    return database.get(user_id)

@jot.instrument(category='auth')
def authenticate(token):
    return verify_token(token)

@jot.instrument('request_id')
def handle_request(data):
    # request_id is extracted for span tags, not passed to function
    process(data)

handle_request(data, request_id='req-123')  # request_id used for span only
```

## Core Classes

### `Meter`

Instrumentation context that holds active span and tags.

**Constructor:** `Meter(target=None, active_span=None, **tags)`

**Methods:**
- `span(name, **tags)` - Create child span
- `start(name=None, **tags)` - Start span
- `finish(**tags)` - Finish active span
- `debug/info/warning(message, **tags)` - Log with span context
- `error(message, exception, **tags)` - Report error
- `count/magnitude(name, value, **tags)` - Record metrics
- `event(name, **tags)` - Record event

### `Span`

Represents a trace segment.

**Constructor:** `Span(trace_id=None, parent_id=None, name=None)`

**Attributes:**
- `id` (str) - Unique span ID
- `trace_id` (str) - Trace ID this span belongs to
- `parent_id` (str) - Parent span ID
- `name` (str) - Span name
- `start_time` (int) - Start timestamp (nanoseconds)
- `end_time` (int) - End timestamp (nanoseconds)
- `is_finished` (bool) - Whether span is complete

**Methods:**
- `start()` - Mark span as started
- `finish()` - Mark span as finished

## Targets

Base class and implementations for telemetry destinations.

### `Target`

Base class for all telemetry targets.

**Constructor:** `Target(level=None)`

**Methods:**
- `accepts_log_level(level)` - Check if log level is accepted
- `start(tags, span)` - Called when span starts
- `finish(tags, span)` - Called when span finishes
- `event(name, tags, span)` - Handle events
- `log(level, message, tags, span)` - Handle log messages
- `error(message, exception, tags, span)` - Handle errors
- `magnitude(name, value, tags, span)` - Handle point-in-time metrics
- `count(name, value, tags, span)` - Handle cumulative metrics

### `PrintTarget`

Prints telemetry to console/stderr.

**Constructor:** `PrintTarget(level=log.DEFAULT, file=sys.stderr)`

**Example:**
```python
from jot.print import PrintTarget
jot.init(PrintTarget())
```

### `OTLPTarget`

Sends telemetry to OpenTelemetry collectors.

**Constructor:** `OTLPTarget(span_exporter, metric_exporter, log_exporter, resource_attributes=None)`

**Class Methods:**
- `default(level)` - Create with default localhost endpoints

**Example:**
```python
from jot.otlp import OTLPTarget
target = OTLPTarget.default()
# or
target = OTLPTarget(
    span_exporter=OTLPSpanExporter('http://jaeger:14268'),
    log_exporter=OTLPLogExporter('http://collector:4318/v1/logs')
)
jot.init(target)
```

### `SentryTarget`

Sends telemetry to Sentry.

**Constructor:** `SentryTarget(dsn=None, level=log.WARNING, **sentry_kwargs)`

**Class Methods:**
- `init_sentry(**kwargs)` - Initialize Sentry SDK

**Example:**
```python
from jot.sentry import SentryTarget
target = SentryTarget(dsn='https://...@sentry.io/...')
jot.init(target)
```

### `RollbarTarget`

Sends errors to Rollbar.

**Constructor:** `RollbarTarget(access_token=None, environment='development', level=log.NOTHING, **kwargs)`

**Example:**
```python
from jot.rollbar import RollbarTarget
target = RollbarTarget(access_token='rollbar_token')
jot.init(target)
```

### `FanOutTarget`

Forwards telemetry to multiple targets.

**Constructor:** `FanOutTarget(*targets, level=None)`

**Example:**
```python
from jot.fanout import FanOutTarget
from jot.print import PrintTarget
from jot.sentry import SentryTarget

target = FanOutTarget(
    PrintTarget(),
    SentryTarget(dsn='...')
)
jot.init(target)
```

### `LoggerTarget`

Bridges to Python's logging system.

**Constructor:** `LoggerTarget(name='', level=log.DEFAULT)`

**Example:**
```python
from jot.logger import LoggerTarget
target = LoggerTarget('myapp')
jot.init(target)
```

### `ZipkinTarget`

Sends traces to Zipkin.

**Constructor:** `ZipkinTarget(url, level=None)`

**Class Methods:**
- `default(level)` - Create with localhost:9411

**Example:**
```python
from jot.zipkin import ZipkinTarget
target = ZipkinTarget('http://zipkin:9411/api/v2/spans'ß)
jot.init(target)
```

## Logging Integration

### `jot.handle_logs(logger)`

Route Python logging records through Jot.

**Parameters:**
- `logger` - Python Logger instance

**Example:**
```python
import logging
jot.handle_logs(logging.getLogger())
# Now logging.info() calls go through Jot targets
```

### `jot.ignore_logs(logger)`

Stop routing logger through Jot.

**Parameters:**
- `logger` - Python Logger instance

## Log Levels

Constants for controlling telemetry verbosity.

- `jot.log.DEBUG` - Debug messages
- `jot.log.INFO` - Info messages
- `jot.log.WARNING` - Warning messages
- `jot.log.NOTHING` - No log messages
- `jot.log.DEFAULT` - Default level (INFO)
- `jot.log.ALL` - All messages

**Example:**
```python
from jot import log
target = PrintTarget(level=log.WARNING)  # Only warnings+
```

## Utilities

### `jot.flush.add_handler(func)`

Register cleanup function called during process shutdown.

**Parameters:**
- `func` - Callable with no arguments

Used internally by targets that need graceful shutdown.
