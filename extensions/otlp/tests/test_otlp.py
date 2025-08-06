import pytest
from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.trace import StatusCode

from jot import log, util
from jot.base import Span
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
def span():
    span = Span(name="test_span")
    span.start()
    return span


@pytest.fixture
def expected_trace_id(span):
    return int.from_bytes(span.trace_id, "big")


@pytest.fixture
def expected_span_id(span):
    return int.from_bytes(span.id, "big")


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


def test_resource_attributes():
    target = OTLPTarget(resource_attributes={"service.name": "test-service"})
    assert target.resource.attributes["service.name"] == "test-service"


def test_no_exporters(span):
    target = OTLPTarget(span_exporter=None, log_exporter=None, metric_exporter=None, level=log.ALL)
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


def test_finish_root(target, span, tags, get_span, expected_trace_id, expected_span_id):
    span.start()
    target.finish(tags, span)

    assert target.span_exporter.export.called_once()
    otspan = get_span()
    assert otspan.context.trace_id == expected_trace_id
    assert otspan.context.span_id == expected_span_id
    assert otspan.parent is None
    for k, v in tags.items():
        assert otspan.attributes[k] == v


def test_finish_child(target, tags, get_span):
    trace_id = util.generate_trace_id()
    parent_id = util.generate_span_id()
    span_id = util.generate_span_id()
    span = Span(trace_id=trace_id, parent_id=parent_id, id=span_id, name="test_span")
    span.start()
    target.finish(tags, span)

    expected_trace_id = int.from_bytes(trace_id, "big")
    expected_span_id = int.from_bytes(span_id, "big")
    expected_parent_id = int.from_bytes(parent_id, "big")

    assert target.span_exporter.export.called_once()
    otspan = get_span()
    assert otspan.name == "test_span"
    assert otspan.context.trace_id == expected_trace_id
    assert otspan.context.span_id == expected_span_id
    assert otspan.parent.trace_id == expected_trace_id
    assert otspan.parent.span_id == expected_parent_id
    for k, v in tags.items():
        assert otspan.attributes[k] == v


def test_log_debug(target, span, tags, get_log, expected_trace_id, expected_span_id):
    target.log(log.DEBUG, "test_log", tags, span)

    assert target.log_exporter.export.called_once()
    log_data = get_log()
    log_record = log_data.log_record
    assert isinstance(log_record.timestamp, int)
    assert log_record.trace_id == expected_trace_id
    assert log_record.span_id == expected_span_id
    assert log_record.severity_text == "debug"
    assert log_record.severity_number == SeverityNumber.DEBUG
    assert log_record.body == "test_log"
    for k, v in tags.items():
        assert log_record.attributes[k] == v


def test_log_info(target, span, tags, get_log, expected_trace_id, expected_span_id):
    target.log(log.INFO, "test_log", tags, span)

    assert target.log_exporter.export.called_once()
    log_data = get_log()
    log_record = log_data.log_record
    assert isinstance(log_record.timestamp, int)
    assert log_record.trace_id == expected_trace_id
    assert log_record.span_id == expected_span_id
    assert log_record.severity_text == "info"
    assert log_record.severity_number == SeverityNumber.INFO
    assert log_record.body == "test_log"
    for k, v in tags.items():
        assert log_record.attributes[k] == v


def test_log_warning(target, span, tags, get_log, expected_trace_id, expected_span_id):
    target.log(log.WARNING, "test_log", tags, span)

    assert target.log_exporter.export.called_once()
    log_data = get_log()
    log_record = log_data.log_record
    assert isinstance(log_record.timestamp, int)
    assert log_record.trace_id == expected_trace_id
    assert log_record.span_id == expected_span_id
    assert log_record.severity_text == "warning"
    assert log_record.severity_number == SeverityNumber.WARN
    assert log_record.body == "test_log"
    for k, v in tags.items():
        assert log_record.attributes[k] == v


def test_log_critical(target, span, tags, get_log, expected_trace_id, expected_span_id):
    target.log(log.CRITICAL, "test_log", tags, span)
    assert target.log_exporter.export.called_once()
    log_data = get_log()
    log_record = log_data.log_record
    assert isinstance(log_record.timestamp, int)
    assert log_record.trace_id == expected_trace_id
    assert log_record.span_id == expected_span_id
    assert log_record.severity_text == "critical"
    assert log_record.severity_number == SeverityNumber.FATAL
    assert log_record.body == "test_log"
    for k, v in tags.items():
        assert log_record.attributes[k] == v


def test_magnitude(target, span, tags, get_metric):
    target.magnitude("test_magnitude", 1.0, tags, span)

    assert target.metric_exporter.export.called_once()
    metric = get_metric()
    assert metric.name == "test_magnitude"
    assert metric.data.data_points[0].value == 1.0
    assert metric.data.data_points[0].attributes == tags
    assert metric.data.data_points[0].start_time_unix_nano == span.start_time
    assert metric.data.data_points[0].time_unix_nano >= span.start_time


def test_count(target, span, tags, get_metric):
    target.count("test_count", 24, tags, span)

    assert target.metric_exporter.export.called_once()
    metric = get_metric()
    assert metric.name == "test_count"
    assert metric.data.data_points[0].value == 24
    assert metric.data.data_points[0].attributes == tags
    assert metric.data.data_points[0].start_time_unix_nano == span.start_time
    assert metric.data.data_points[0].time_unix_nano >= span.start_time


def test_event(target, span, tags, get_span):
    target.event("test_event", tags, span)
    target.finish({}, span)

    assert target.span_exporter.export.called_once()
    otspan = get_span()
    assert otspan.events[0].name == "test_event"
    assert otspan.events[0].attributes == tags
    assert otspan.events[0].timestamp >= span.start_time


def test_error(target, span, tags, get_span):
    print(span.trace_id)
    try:
        raise ValueError("test_error")
    except ValueError as e:
        target.error("test_error", e, tags, span)
    target.finish({}, span)

    assert target.span_exporter.export.called_once()
    otspan = get_span()
    assert otspan.status.status_code == StatusCode.ERROR
    assert otspan.events[0].name == "test_error"
    assert otspan.events[0].timestamp >= span.start_time
    assert otspan.events[0].attributes["exception.type"] == "ValueError"
    assert otspan.events[0].attributes["exception.message"] == "test_error"
    assert otspan.events[0].attributes["exception.stacktrace"] is not None
    assert (
        otspan.events[0]
        .attributes["exception.stacktrace"]
        .startswith("Traceback (most recent call last):")
    )
    assert otspan.events[0].attributes["exception.stacktrace"].endswith("ValueError: test_error\n")


def test_log_bytes_tag(target, span):
    tags = {"biff": b"bytes for testing"}
    target.log(log.INFO, "norf", tags)

    assert target.log_exporter.export.called_once()
    log_data = target.log_exporter.export.call_args[0][0][0]
    log_record = log_data.log_record
    assert log_record.attributes["biff"] == "627974657320666f722074657374696e67"


def test_error_bytes_tag(target, span, get_span):
    try:
        raise ValueError("test_error")
    except ValueError as e:
        tags = {"biff": b"bytes for testing"}
        target.error("test_error", e, tags, span)
    target.finish({}, span)

    assert target.span_exporter.export.called_once()
    otspan = get_span()
    print(repr(otspan.events[0].attributes))
    assert otspan.events[0].attributes["biff"] == "627974657320666f722074657374696e67"


def test_magnitude_bytes_tag(target, span):
    tags = {"biff": b"bytes for testing"}
    target.magnitude("test_magnitude", 1.0, tags, span)

    assert target.metric_exporter.export.called_once()
    arg = target.metric_exporter.export.call_args[0][0]
    point = arg.resource_metrics[0].scope_metrics[0].metrics[0].data.data_points[0]
    assert point.attributes["biff"] == "627974657320666f722074657374696e67"


def test_count_bytes_tag(target, span):
    tags = {"biff": b"bytes for testing"}
    target.count("test_count", 24, tags, span)

    assert target.metric_exporter.export.called_once()
    arg = target.metric_exporter.export.call_args[0][0]
    point = arg.resource_metrics[0].scope_metrics[0].metrics[0].data.data_points[0]
    assert point.attributes["biff"] == "627974657320666f722074657374696e67"


def test_finish_bytes_tag(target, span, get_span, expected_trace_id, expected_span_id):
    tags = {"biff": b"bytes for testing"}
    span.start()
    target.finish(tags, span)

    assert target.span_exporter.export.called_once()
    otspan = get_span()
    assert otspan.attributes["biff"] == "627974657320666f722074657374696e67"


def test_from_environment_with_all_exporters(monkeypatch):
    """Test OTLPTarget.from_environment with all exporters configured"""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_LOGS_ENDPOINT", "http://localhost:4317/v1/logs")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "http://localhost:4317/v1/metrics")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://localhost:4317/v1/traces")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "test-service")

    # We need to mock the exporters to avoid actual connections
    from unittest.mock import patch

    with (
        patch("jot.otlp.otlp._env_log_exporter") as mock_log_exporter,
        patch("jot.otlp.otlp._env_metric_exporter") as mock_metric_exporter,
        patch("jot.otlp.otlp._env_span_exporter") as mock_span_exporter,
    ):
        # Configure our mocks to return non-None values
        mock_log_exporter.return_value = object()
        mock_metric_exporter.return_value = object()
        mock_span_exporter.return_value = object()

        target = OTLPTarget.from_environment()

        assert target is not None
        assert target.log_exporter is mock_log_exporter.return_value
        assert target.metric_exporter is mock_metric_exporter.return_value
        assert target.span_exporter is mock_span_exporter.return_value
        assert target.resource.attributes["service.name"] == "test-service"


def test_from_environment_with_just_service_name(monkeypatch):
    """Test OTLPTarget.from_environment with just service name set but no exporters"""
    monkeypatch.setenv("SERVICE_NAME", "test-service-only")

    # Clear any existing environment variables that might affect the test
    for var in [
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT",
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    ]:
        monkeypatch.delenv(var, raising=False)

    # We need to mock the exporters to return None (no configuration)
    from unittest.mock import patch

    with (
        patch("jot.otlp.otlp._env_log_exporter") as mock_log_exporter,
        patch("jot.otlp.otlp._env_metric_exporter") as mock_metric_exporter,
        patch("jot.otlp.otlp._env_span_exporter") as mock_span_exporter,
    ):
        # Configure our mocks to return None values
        mock_log_exporter.return_value = None
        mock_metric_exporter.return_value = None
        mock_span_exporter.return_value = None

        target = OTLPTarget.from_environment()

        # Should return None when no exporters are configured
        assert target is None


def test_from_environment_with_log_exporter_only(monkeypatch):
    """Test OTLPTarget.from_environment with only log exporter configured"""
    monkeypatch.setenv("SERVICE_NAME", "log-service")

    # We need to mock the exporters to have only log exporter configured
    from unittest.mock import patch

    with (
        patch("jot.otlp.otlp._env_log_exporter") as mock_log_exporter,
        patch("jot.otlp.otlp._env_metric_exporter") as mock_metric_exporter,
        patch("jot.otlp.otlp._env_span_exporter") as mock_span_exporter,
    ):
        # Configure our mocks to return appropriate values
        mock_log_exporter.return_value = object()
        mock_metric_exporter.return_value = None
        mock_span_exporter.return_value = None

        target = OTLPTarget.from_environment()

        assert target is not None
        assert target.log_exporter is mock_log_exporter.return_value
        assert target.metric_exporter is None
        assert target.span_exporter is None
        assert target.resource.attributes["service.name"] == "log-service"


def test_from_environment_with_otel_service_name(monkeypatch):
    """Test OTLPTarget.from_environment with OTEL_SERVICE_NAME env var"""
    monkeypatch.setenv("OTEL_SERVICE_NAME", "otel-named-service")
    monkeypatch.delenv("SERVICE_NAME", raising=False)

    # We need to mock the exporters to have one exporter configured
    from unittest.mock import patch

    with (
        patch("jot.otlp.otlp._env_log_exporter") as mock_log_exporter,
        patch("jot.otlp.otlp._env_metric_exporter") as mock_metric_exporter,
        patch("jot.otlp.otlp._env_span_exporter") as mock_span_exporter,
    ):
        # Configure our mocks to return appropriate values
        mock_log_exporter.return_value = None
        mock_metric_exporter.return_value = object()
        mock_span_exporter.return_value = None

        target = OTLPTarget.from_environment()

        assert target is not None
        assert target.log_exporter is None
        assert target.metric_exporter is mock_metric_exporter.return_value
        assert target.span_exporter is None
        assert target.resource.attributes["service.name"] == "otel-named-service"
