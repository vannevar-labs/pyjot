# Pyjot Quick Reference

Cheat sheet for common telemetry patterns.

## Setup

```python
import jot
from jot.print import PrintTarget

# Development
jot.init(PrintTarget())

# Production
from jot.otlp import OTLPTarget
jot.init(OTLPTarget.default(), service="my-app", env="prod")
```

## Logging

```python
jot.debug("SQL query", {"query": "SELECT * FROM users", "duration_ms": 45})
jot.info("User action", {"user_id": 123, "action": "login"})
jot.warning("Rate limit hit", {"endpoint": "/api", "remaining": 0})
```

## Metrics

```python
# Counters (cumulative)
jot.count("requests", 1, {"method": "GET", "status": 200})
jot.count("errors", 1, {"type": "validation"})

# Gauges (point-in-time)
jot.magnitude("memory_mb", 512)
jot.magnitude("queue_depth", 42, {"queue": "jobs"})
```

## Error Tracking

```python
try:
    dangerous_operation()
except Exception as e:
    jot.error("Operation failed", e, {"user_id": 123})
```

## Function Tracing

```python
# Basic
@jot.instrument
def process_data(data):
    return transform(data)

# With category
@jot.instrument(category="database")
def save_user(user):
    db.save(user)

# With dynamic tags
@jot.instrument("request_id")
def handle_request(payload):
    return process(payload)

handle_request(data, request_id="req-123")  # request_id extracted for span, not passed to function
```

## Manual Spans

```python
# Context manager
with jot.span("cache_lookup", key="user:123"):
    result = cache.get("user:123")
    jot.info("Cache result", {"hit": result is not None})

# Manual control
span = jot.start("operation")
try:
    do_work()
finally:
    jot.finish(status="complete")
```

## Multiple Targets

```python
from jot.fanout import FanOutTarget
from jot.print import PrintTarget
from jot.sentry import SentryTarget

target = FanOutTarget(
    PrintTarget(),  # Console output
    SentryTarget(dsn="...")  # Error tracking
)
jot.init(target)
```

## Python Logging Bridge

```python
import logging

# Route stdlib logging through Jot
jot.handle_logs(logging.getLogger())

# Now this goes to Jot targets:
logging.info("Standard log message", extra={"user_id": 123})
```

## Common Targets

```python
# Console (development)
from jot.print import PrintTarget
jot.init(PrintTarget())

# OpenTelemetry (production)
from jot.otlp import OTLPTarget
jot.init(OTLPTarget("http://collector:4318"))

# Sentry (errors)
from jot.sentry import SentryTarget
jot.init(SentryTarget(dsn="https://..."))

# Rollbar (errors)
from jot.rollbar import RollbarTarget
jot.init(RollbarTarget(access_token="..."))
```

## Configuration Patterns

```python
import os

# Conditional setup
if os.getenv("SENTRY_DSN"):
    jot.init(SentryTarget(dsn=os.getenv("SENTRY_DSN")))
elif os.getenv("DEBUG"):
    jot.init(PrintTarget())
# else: no telemetry (all jot calls become no-ops)

# Global tags
jot.init(target, {
    "service": "my-service",
    "version": os.getenv("VERSION", "unknown"),
    "environment": os.getenv("ENV", "development")
})
```

## Web Framework Integration

```python
# FastAPI
@jot.instrument(category="api")
async def process_request(data):
    result = await business_logic(data)
    jot.info("Request processed", {"result_size": len(result)})
    return result

@app.post("/process")
async def process_endpoint(data: RequestData):
    return await process_request(data.dict())
```

## Database Queries

```python
# Automatic psycopg2 instrumentation
import psycopg2
from jot.pg import JotCursor

conn = psycopg2.connect("postgresql://...", cursor_factory=JotCursor)
cursor = conn.cursor()

# Queries are automatically traced with spans and metrics
cursor.execute("SELECT * FROM users WHERE active = %s", (True,))
users = cursor.fetchall()  # Automatically creates "query" span with SQL and args

# Manual instrumentation for other databases
@jot.instrument(category="database")
def execute_query(sql, params=None):
    result = db.execute(sql, params)
    jot.info("Query executed", {"sql": sql, "rows": len(result)})
    return result
```

## Background Jobs

```python
@jot.instrument("job_id")
def process_job(job_data):
    jot.info("Job started", {"type": job_data["type"]})

    try:
        result = do_work(job_data)
        jot.info("Job completed", {"result_size": len(result)})
        return result
    except Exception as e:
        jot.error("Job failed", e, {"retry_count": job_data.get("retries", 0)})
        raise
```
