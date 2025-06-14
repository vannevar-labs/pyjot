from prometheus_client import Counter, Gauge, Histogram, Summary, start_http_server

from . import flush
from .base import Target


class PrometheusTarget(Target):
    def __init__(self, level=0, port=8080):
        super().__init__(level)
        self.metrics = {}
        if port is not None:
            _init_prometheus(port)

    def add_metric(self, metric):
        self.metrics[metric._name] = metric

    def _record_metric(self, metric_class, name, value, tags):
        metric = self.metrics.get(name)
        if metric is None:
            metric = metric_class(name, "Jot automatic metric", tags.keys())
            self.add_metric(metric)

        if isinstance(metric, Gauge):
            metric.labels(**tags).set(value)
        elif isinstance(metric, Counter):
            metric.labels(**tags).inc(value)
        elif isinstance(metric, Histogram):
            metric.labels(**tags).observe(value)
        elif isinstance(metric, Summary):
            metric.labels(**tags).observe(value)
        else:
            raise ValueError(f"Unsupported metric type: {type(metric)}")

    def magnitude(self, name, value, tags, span=None):
        self._record_metric(Gauge, name, value, tags)

    def count(self, name, value, tags, span=None):
        self._record_metric(Counter, name, value, tags)


_server = None
_thread = None
_port = 8080


def _init_prometheus(port):
    global _server, _thread, _port
    if _server is not None:
        if port != _port:
            raise ValueError(f"Prometheus server is already running on port {_port}.")
        return

    _port = port
    _server, _thread = start_http_server(port)
    flush.add_handler(_shut_down)


def _shut_down():
    global _server, _thread
    if _server is not None and _thread is not None:
        _server.shutdown()
        _thread.join(3.0)
