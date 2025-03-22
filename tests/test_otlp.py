import pytest
from opentelemetry._logs.severity import SeverityNumber

from jot import log
from jot.otlp import OTLPTarget


@pytest.fixture
def tags():
    return {"nork": "flet", "pizz": 65}


@pytest.fixture
def target(mocker):
    se = mocker.MagicMock()
    le = mocker.MagicMock()
    me = mocker.MagicMock()
    return OTLPTarget(span_exporter=se, log_exporter=le, metric_exporter=me, level=log.ALL)


@pytest.fixture
def get_span(target):
    def get_span():
        return target.span_exporter.export.call_args[0][0][0]

    return get_span


@pytest.fixture
def get_log(target):
    def get_export():
        return target.log_exporter.export.call_args[0][0][0]

    return get_export


@pytest.fixture
def get_metric(target):
    def get_metric():
        metrics_data = target.metric_exporter.export.call_args[0][0]
        rm = metrics_data.resource_metrics[0]
        assert rm.resource is target.resource
        sm = rm.scope_metrics[0]
        assert sm.scope is target.scope
        return sm.metrics[0]

    return get_metric


def test_trace_id():
    target = OTLPTarget.default()
    trace_id = target.generate_trace_id()
    hex_trace_id = target.format_trace_id(trace_id)
    assert isinstance(trace_id, int)
    assert isinstance(hex_trace_id, str)
    assert len(hex_trace_id) == 32


def test_span_id():
    target = OTLPTarget.default()
    span_id = target.generate_span_id()
    hex_span_id = target.format_span_id(span_id)
    assert isinstance(span_id, int)
    assert isinstance(hex_span_id, str)
    assert len(hex_span_id) == 16


def test_no_exporter():
    target = OTLPTarget(span_exporter=None, log_exporter=None, metric_exporter=None, level=log.ALL)
    span = target.start("test_span")
    target.event("test_event", {}, span)
    target.log(log.INFO, "test_log", {}, span)
    try:
        print(1 / 0)
    except ZeroDivisionError as e:
        target.error("test_exception", e, {}, span)
    target.magnitude("test_magnitude", 1.0, {}, span)
    target.count("test_count", 1, {}, span)
    target.finish({}, span)
    # no assertions, just ensure no exceptions are raised


def test_finish_root(target, tags, get_span):
    trace_id = target.generate_trace_id()
    span_id = target.generate_span_id()
    span = target.start(trace_id=trace_id, id=span_id, name="test_span")
    target.finish(tags, span)

    assert target.span_exporter.export.called_once()
    otspan = get_span()
    assert otspan.context.trace_id == trace_id
    assert otspan.context.span_id == span_id
    assert otspan.parent is None
    for k, v in tags.items():
        assert otspan.attributes[k] == v


def test_finish_child(target, tags, get_span):
    trace_id = target.generate_trace_id()
    parent_id = target.generate_span_id()
    span_id = target.generate_span_id()
    span = target.start(trace_id=trace_id, parent_id=parent_id, id=span_id, name="test_span")
    target.finish(tags, span)

    assert target.span_exporter.export.called_once()
    otspan = get_span()
    assert otspan.name == "test_span"
    assert otspan.context.trace_id == trace_id
    assert otspan.context.span_id == span_id
    assert otspan.parent.trace_id == trace_id
    assert otspan.parent.span_id == parent_id
    for k, v in tags.items():
        assert otspan.attributes[k] == v


def test_log_debug(target, tags, get_log):
    span = target.start("test_span")
    target.log(log.DEBUG, "test_log", tags, span)

    assert target.log_exporter.export.called_once()
    log_data = get_log()
    log_record = log_data.log_record
    assert isinstance(log_record.timestamp, int)
    assert log_record.trace_id == span.trace_id
    assert log_record.span_id == span.id
    assert log_record.severity_text == "debug"
    assert log_record.severity_number == SeverityNumber.DEBUG
    assert log_record.body == "test_log"
    for k, v in tags.items():
        assert log_record.attributes[k] == v


def test_log_info(target, tags, get_log):
    span = target.start("test_span")
    target.log(log.INFO, "test_log", tags, span)

    assert target.log_exporter.export.called_once()
    log_data = get_log()
    log_record = log_data.log_record
    assert isinstance(log_record.timestamp, int)
    assert log_record.trace_id == span.trace_id
    assert log_record.span_id == span.id
    assert log_record.severity_text == "info"
    assert log_record.severity_number == SeverityNumber.INFO
    assert log_record.body == "test_log"
    for k, v in tags.items():
        assert log_record.attributes[k] == v


def test_log_warning(target, tags, get_log):
    span = target.start("test_span")
    target.log(log.WARNING, "test_log", tags, span)

    assert target.log_exporter.export.called_once()
    log_data = get_log()
    log_record = log_data.log_record
    assert isinstance(log_record.timestamp, int)
    assert log_record.trace_id == span.trace_id
    assert log_record.span_id == span.id
    assert log_record.severity_text == "warning"
    assert log_record.severity_number == SeverityNumber.WARN
    assert log_record.body == "test_log"
    for k, v in tags.items():
        assert log_record.attributes[k] == v


def test_log_critical(target, tags, get_log):
    span = target.start("test_span")
    target.log(log.CRITICAL, "test_log", tags, span)

    assert target.log_exporter.export.called_once()
    log_data = get_log()
    log_record = log_data.log_record
    assert isinstance(log_record.timestamp, int)
    assert log_record.trace_id == span.trace_id
    assert log_record.span_id == span.id
    assert log_record.severity_text == "critical"
    assert log_record.severity_number == SeverityNumber.FATAL
    assert log_record.body == "test_log"
    for k, v in tags.items():
        assert log_record.attributes[k] == v


def test_magnitude(target, tags, get_metric):
    span = target.start("test_span")
    target.magnitude("test_magnitude", 1.0, tags, span)

    assert target.metric_exporter.export.called_once()
    metric = get_metric()
    assert metric.name == "test_magnitude"
    assert metric.data.data_points[0].value == 1.0
    assert metric.data.data_points[0].attributes == tags
    assert metric.data.data_points[0].start_time_unix_nano == span.start_time
    assert metric.data.data_points[0].time_unix_nano >= span.start_time


def test_count(target, tags, get_metric):
    span = target.start("test_span")
    target.count("test_count", 24, tags, span)

    assert target.metric_exporter.export.called_once()
    metric = get_metric()
    assert metric.name == "test_count"
    assert metric.data.data_points[0].value == 24
    assert metric.data.data_points[0].attributes == tags
    assert metric.data.data_points[0].start_time_unix_nano == span.start_time
    assert metric.data.data_points[0].time_unix_nano >= span.start_time
