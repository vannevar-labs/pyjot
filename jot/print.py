from sys import stderr
from time import time
from traceback import print_exception
from .base import Target

class PrintTarget(Target):
  """A target the prints telemetry to stderr"""

  @staticmethod
  def _write(span, tags=None, *chunks):
    stderr.write(f"[{span._now()}]")
    if type(tags) == dict:
      for k,v in tags.items():
        stderr.write(f" {k}={v}")
    else:
      stderr.write(f" tags")
    for c in chunks:
      stderr.write(f" {c}")
    stderr.write("\n")
  
  def finish(self, span, tags):
    tags["duration"] = span.duration
    self._write(span, tags, "finish", span.name)

  def log(self, span,  level, message, tags):
    self._write(span, tags, level, message)

  def error(self, span, message, exception, tags):
    self._write(span, tags, "Error:", message)
    print_exception(exception)

  def magnitude(self, span, name, value, tags):
    self._write(span, tags, f"{name}={value}")

  def count(self, span, name, value, tags):
    self._write(span, tags, f"{name}={value}")
