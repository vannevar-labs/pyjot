from time import time_ns

from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LogData, LogRecord
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    Gauge,
    Metric,
    MetricsData,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
    Sum,
)
from opentelemetry.sdk.resources import (
    OsResourceDetector,
    OTELResourceDetector,
    ProcessResourceDetector,
    Resource,
    get_aggregated_resources,
)
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import (
    SpanContext,
    SpanKind,
    Status,
    StatusCode,
    TraceFlags,
    format_span_id,
    format_trace_id,
)

from jot import log

from .base import Target

SCHEMA_URL = "https://opentelemetry.io/schemas/1.21.0"

_generator = RandomIdGenerator()

_severity_map = {
    log.DEBUG: SeverityNumber.DEBUG,
    log.INFO: SeverityNumber.INFO,
    log.WARNING: SeverityNumber.WARN,
    log.ERROR: SeverityNumber.ERROR,
    log.CRITICAL: SeverityNumber.FATAL,
}


class OTLPTarget(Target):
    @classmethod
    def default(cls, level=log.DEFAULT):
        span_exporter = OTLPSpanExporter("http://localhost:4318/v1/traces")
        metric_exporter = OTLPMetricExporter("http://localhost:4318/v1/metrics")
        log_exporter = OTLPLogExporter("http://localhost:4318/v1/logs")
        return cls(
            span_exporter=span_exporter,
            metric_exporter=metric_exporter,
            log_exporter=log_exporter,
            level=level,
        )

    def __init__(self, span_exporter=None, log_exporter=None, metric_exporter=None, level=None):
        super().__init__(level)
        self.span_exporter = span_exporter
        self.log_exporter = log_exporter
        self.metric_exporter = metric_exporter
        self.resource = _create_resource()
        self.scope = InstrumentationScope("unknown", version=None, schema_url=SCHEMA_URL)
        self.span_data = {}

    @staticmethod
    def generate_trace_id():  # type: ignore
        return _generator.generate_trace_id()

    @staticmethod
    def generate_span_id():  # type: ignore
        return _generator.generate_span_id()

    @staticmethod
    def format_trace_id(trace_id):
        return format_trace_id(trace_id)

    @staticmethod
    def format_span_id(span_id):
        return format_span_id(span_id)

    def start(self, trace_id=None, parent_id=None, id=None, name=None):
        span = super().start(trace_id, parent_id, id, name)
        self.span_data[span.id] = OtelSpanData()
        return span

    def log(self, level, message, tags, span=None):
        if self.log_exporter is None:
            return

        log_record = LogRecord(
            timestamp=time_ns(),
            trace_id=span.trace_id if span else None,
            span_id=span.id if span else None,
            trace_flags=TraceFlags.get_default(),
            severity_text=log.name(level),
            severity_number=_severity_map.get(level),
            body=message,
            resource=self.resource,
            attributes=tags,
        )
        log_data = LogData(log_record, self.scope)
        self.log_exporter.export([log_data])

    def magnitude(self, name, value, tags, span=None):
        if self.metric_exporter is None:
            return

        # this absurdity is brought to you by the opentelemetry sdk
        now = time_ns()
        dp = NumberDataPoint(
            attributes=tags,
            start_time_unix_nano=span.start_time if span else now,
            time_unix_nano=now,
            value=value,
        )
        gauge = Gauge([dp])
        metric = Metric(name, description=None, unit=None, data=gauge)
        scope_metrics = ScopeMetrics(
            scope=self.scope,
            metrics=[metric],
            schema_url=SCHEMA_URL,
        )
        resource_metrics = ResourceMetrics(
            resource=self.resource,
            scope_metrics=[scope_metrics],
            schema_url=SCHEMA_URL,
        )
        data = MetricsData(resource_metrics=[resource_metrics])

        self.metric_exporter.export(data)

    def count(self, name, value, tags, span=None):
        if self.metric_exporter is None:
            return

        # this absurdity is brought to you by the opentelemetry sdk
        now = time_ns()
        dp = NumberDataPoint(
            attributes=tags,
            start_time_unix_nano=span.start_time if span else now,
            time_unix_nano=now,
            value=value,
        )
        gauge = Sum([dp], aggregation_temporality=AggregationTemporality.DELTA, is_monotonic=True)
        metric = Metric(name, description=None, unit=None, data=gauge)
        scope_metrics = ScopeMetrics(
            scope=self.scope,
            metrics=[metric],
            schema_url=SCHEMA_URL,
        )
        resource_metrics = ResourceMetrics(
            resource=self.resource,
            scope_metrics=[scope_metrics],
            schema_url=SCHEMA_URL,
        )
        data = MetricsData(resource_metrics=[resource_metrics])

        self.metric_exporter.export(data)

    def finish(self, tags, span):
        if self.span_exporter is None:
            return
        span_data = self.span_data.pop(span.id, None)
        if span_data is None:
            print("span_data is None", flush=True)
            return

        span_data.finish(tags)
        ot_span = span_data.create_readable_span(self.resource, span)
        self.span_exporter.export([ot_span])


class OtelSpanData:
    def __init__(self):
        self.events = []
        self.attributes = {}
        self.kind = SpanKind.INTERNAL
        self.status = None

    def add_event(self, event):
        self.events.append(event)

    def note_error(self, error):
        self.status = Status(StatusCode.ERROR, str(error))

    def finish(self, tags):
        self.attributes.update(tags)

        if self.status is None:
            self.status = Status(StatusCode.OK)

    def create_readable_span(self, resource, span):
        status = self.status if self.status else Status(StatusCode.OK)
        parent = (
            SpanContext(span.trace_id, span.parent_id, is_remote=False) if span.parent_id else None
        )

        return ReadableSpan(
            name=span.name,
            context=SpanContext(span.trace_id, span.id, is_remote=False),
            parent=parent,
            resource=resource,
            attributes=self.attributes,
            events=self.events,
            links=[],
            kind=self.kind,
            instrumentation_info=None,
            status=status,
            start_time=span.start_time,
            end_time=span.finish_time,
            instrumentation_scope=None,
        )


def _create_resource():
    initial = Resource(attributes={}, schema_url=SCHEMA_URL)
    detectors = [OTELResourceDetector(), ProcessResourceDetector(), OsResourceDetector()]
    aggregated = get_aggregated_resources(detectors, initial_resource=initial)
    return aggregated
