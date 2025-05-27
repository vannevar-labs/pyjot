Jot
===

A library for instrumenting code and sending telemetry information to an aggregator.


## Example

```python
import jot
from jot.print import PrintTarget

# A target provides the destination for the telemetry data. If jot is not initialized, all
# telemetry will be ignored. `init()` also accepts a dictionary of tags to be applied to all
# logs, metrics, errors and traces.
jot.init(PrintTarget(), {"environment": "staging"})

# Three levels of logging, with structured data
jot.debug("debug message", {"more": "tags"})
jot.info("info message", {"numeric": 64})
jot.warning("uh oh", {"level_of_concern": 6})

# Magnitudes are point-in-time measurements
jot.magnitude("memory-usage-bytes", 8096, {"executable": false})

# Counts are cumulative
jot.count("requests", 3, {"http.status": 200})

# Error reporting collects stack traces for analysis
try:
  1/0
except ZeroDivisionError as exc:
  jot.error("Error calculating sales tax", exc, {"customer_id": 1337})

# instrument functions to create traces
@instrument
def add(a, b):
    # adds a span named 'add' to the current trace
    jot.debug("Adding numbers", {"a": a, "b": b})
    return a + b

@instrument(category="math")
def multiply(a, b):
    # 'category': 'math' will be automatically added to log message
    jot.debug("Multiplying numbers", {"a": a, "b": b})
    return a * b

@instrument('customer_id')
def subtract(a, b):
    # subtract now accepts a keyword argument 'customer_id' to add to the trace
    jot.debug("Subtracting numbers", {"a": a, "b": b})
    return a - b

add()
multiply(3, 4)
subtract(10, 5, customer_id=1337)



```
