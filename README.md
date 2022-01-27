Jot
===

A library for instrumenting code and sending telemetry information to an aggregator. 


## Example

```python
import jot

# A target provides the destination for the telemetry data. If jot is not initialized, all 
# telemetry will be ignored. `init()` also accepts a dictionary of tags to be applied to all
# logs, metrics, errors and traces.
jot.init(TargetClass(), {"environment": "staging"})

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

# Traces for application performance monitoring
with jot.span("task", trace_id=544678, parent_id=None, {"importance": "high"}):
  with jot.span("subtask 1"):
    sleep(1)
    jot.info("feeling refreshed")
  with jot.span("subtask 2"):
    sleep(0.2)
    jot.warning("didn't get enough sleep")
```
