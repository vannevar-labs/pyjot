import time

import pytest
import requests_mock

from jot.base import Span


@pytest.fixture
def span():
    span = Span()
    span.start()
    return span


@pytest.fixture(params=[pytest.param("v2", id="influxdb2"), pytest.param("v3", id="influxdb3")])
def target(request):
    if request.param == "v2":
        from jot.influxdb import InfluxDB2Target

        return InfluxDB2Target(
            endpoint="http://localhost:8086",
            bucket="test-db",
            token="test-token",
        )
    else:
        from jot.influxdb import InfluxDB3Target

        return InfluxDB3Target(
            endpoint="http://localhost:8086",
            database="test-db",
            token="test-token",
        )


@pytest.fixture
def mock_requests():
    """Fixture for mocking HTTP requests"""
    with requests_mock.Mocker() as m:
        yield m


@pytest.fixture
def sample_tags():
    """Sample tags for testing"""
    return {"service": "test-app", "environment": "test", "host": "localhost"}


@pytest.fixture
def expected_headers():
    """Expected HTTP headers for InfluxDB requests"""
    return {"Authorization": "Bearer test-token", "Content-Type": "text/plain"}


def test_constructor_v2():
    """Test that InfluxDB2Target constructor parameters are processed correctly"""
    from jot.influxdb import InfluxDB2Target

    target = InfluxDB2Target(endpoint="http://localhost:8086", bucket="test-db", token="test-token")

    assert target.url == "http://localhost:8086/api/v2/write"
    assert target.params == {"bucket": "test-db"}
    assert target.headers == {"Content-Type": "text/plain", "Authorization": "Bearer test-token"}
    assert hasattr(target, "session")
    assert target.session is not None


def test_constructor_v3():
    """Test that InfluxDB3Target constructor parameters are processed correctly"""
    from jot.influxdb import InfluxDB3Target

    target = InfluxDB3Target(
        endpoint="http://localhost:8086", database="test-db", token="test-token"
    )

    assert target.url == "http://localhost:8086/api/v3/write_lp"
    assert target.params == {"db": "test-db"}
    assert target.headers == {"Content-Type": "text/plain", "Authorization": "Bearer test-token"}
    assert hasattr(target, "session")
    assert target.session is not None


def test_default_factory_v2():
    """Test the InfluxDB2Target @classmethod def default() method"""
    from jot.influxdb import InfluxDB2Target

    target = InfluxDB2Target.default()
    assert target is not None
    assert target.url == "http://localhost:8086/api/v2/write"
    assert target.params == {"bucket": "default"}


def test_default_factory_v3():
    """Test the InfluxDB3Target @classmethod def default() method"""
    from jot.influxdb import InfluxDB3Target

    target = InfluxDB3Target.default()
    assert target is not None
    assert target.url == "http://localhost:8086/api/v3/write_lp"
    assert target.params == {"db": "default"}


def test_constructor_v2_with_org():
    """Test that InfluxDB2Target constructor includes org parameter when provided"""
    from jot.influxdb import InfluxDB2Target

    target = InfluxDB2Target(
        endpoint="http://localhost:8086", bucket="test-db", token="test-token", org="test-org"
    )

    assert target.url == "http://localhost:8086/api/v2/write"
    assert target.params == {"bucket": "test-db", "org": "test-org"}
    assert target.headers == {"Content-Type": "text/plain", "Authorization": "Bearer test-token"}


def test_send_http_with_org_param_v2(mock_requests):
    """Test that org parameter is included in URL for InfluxDB2Target"""
    from jot.influxdb import InfluxDB2Target

    target = InfluxDB2Target(
        endpoint="http://localhost:8086", bucket="test-db", token="test-token", org="test-org"
    )

    mock_requests.post(target.url, status_code=204)

    target._send("test value=1 1609459200000000000")

    # Verify both bucket and org are in query parameters
    request = mock_requests.last_request
    assert "bucket=test-db" in request.url
    assert "org=test-org" in request.url


def test_format_line_protocol_basic(target):
    """Test basic line protocol formatting with simple values"""
    # Test float value
    result = target._format_line_protocol("cpu_usage", 85.2, {}, 1609459200000000000)
    assert result == "cpu_usage value=85.2 1609459200000000000"

    # Test integer value
    result = target._format_line_protocol("request_count", 42, {"type": "int"}, 1609459200000000000)
    assert result == "request_count,type=int value=42i 1609459200000000000"


def test_format_line_protocol_with_tags(target, sample_tags):
    """Test line protocol formatting with various tag combinations"""
    # Single tag
    result = target._format_line_protocol(
        "memory", 1024.0, {"host": "server1"}, 1609459200000000000
    )
    assert result == "memory,host=server1 value=1024.0 1609459200000000000"

    # Multiple tags (should be sorted for consistency)
    result = target._format_line_protocol("cpu", 75.5, sample_tags, 1609459200000000000)
    assert (
        result
        == "cpu,environment=test,host=localhost,service=test-app value=75.5 1609459200000000000"
    )


def test_format_line_protocol_escaping(target):
    """Test proper escaping of special characters in measurement names and tags"""
    # Test measurement name with spaces and special chars
    result = target._format_line_protocol("cpu usage", 85.2, {}, 1609459200000000000)
    assert result == "cpu\\ usage value=85.2 1609459200000000000"

    # Test tag keys and values with spaces, commas, equals
    result = target._format_line_protocol(
        "metric", 100.0, {"host name": "server 1", "env,type": "prod=main"}, 1609459200000000000
    )
    assert (
        result
        == "metric,env\\,type=prod\\=main,host\\ name=server\\ 1 value=100.0 1609459200000000000"
    )


def test_format_line_protocol_timestamp_precision(target):
    """Test timestamp formatting with nanosecond precision"""
    # Test with specific nanosecond timestamp
    result = target._format_line_protocol("test", 1.0, {}, 1609459200123456789)
    assert result == "test value=1.0 1609459200123456789"

    # Test with zero timestamp
    result = target._format_line_protocol("test", 1.0, {}, 0)
    assert result == "test value=1.0 0"


def test_format_line_protocol_field_types(target):
    """Test proper field type formatting (float vs integer)"""
    # Float values should not have 'i' suffix
    result = target._format_line_protocol("temperature", 23.5, {}, 1609459200000000000)
    assert result == "temperature value=23.5 1609459200000000000"

    # Integer values should have 'i' suffix
    result = target._format_line_protocol("count", 42, {"type": "int"}, 1609459200000000000)
    assert result == "count,type=int value=42i 1609459200000000000"

    # Zero values
    result = target._format_line_protocol("zero_float", 0.0, {}, 1609459200000000000)
    assert result == "zero_float value=0.0 1609459200000000000"

    result = target._format_line_protocol("zero_int", 0, {"type": "int"}, 1609459200000000000)
    assert result == "zero_int,type=int value=0i 1609459200000000000"


def test_format_line_protocol_edge_cases(target):
    """Test edge cases for line protocol formatting"""
    # Negative values
    result = target._format_line_protocol(
        "temperature", -10.5, {"location": "freezer"}, 1609459200000000000
    )
    assert result == "temperature,location=freezer value=-10.5 1609459200000000000"

    # Very large numbers
    result = target._format_line_protocol(
        "bytes", 9223372036854775807, {"type": "int"}, 1609459200000000000
    )
    assert result == "bytes,type=int value=9223372036854775807i 1609459200000000000"

    # Empty tags dictionary
    result = target._format_line_protocol("simple", 42.0, {}, 1609459200000000000)
    assert result == "simple value=42.0 1609459200000000000"


def test_send_http_basic_v2(mock_requests, expected_headers):
    """Test basic HTTP sending functionality for InfluxDB2Target"""
    from jot.influxdb import InfluxDB2Target

    target = InfluxDB2Target(endpoint="http://localhost:8086", bucket="test-db", token="test-token")

    # Mock successful response
    mock_requests.post(target.url, status_code=204)

    # Send a line protocol string
    line_protocol = "cpu_usage value=85.2 1609459200000000000"
    target._send(line_protocol)

    # Verify HTTP call was made correctly
    assert mock_requests.called
    assert mock_requests.call_count == 1

    # Check the request details
    request = mock_requests.last_request
    assert request.url == f"{target.url}?bucket=test-db"
    assert request.method == "POST"
    assert request.text == line_protocol

    # Check headers
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers["Content-Type"] == "text/plain"


def test_send_http_basic_v3(mock_requests, expected_headers):
    """Test basic HTTP sending functionality for InfluxDB3Target"""
    from jot.influxdb import InfluxDB3Target

    target = InfluxDB3Target(
        endpoint="http://localhost:8086", database="test-db", token="test-token"
    )

    # Mock successful response
    mock_requests.post(target.url, status_code=204)

    # Send a line protocol string
    line_protocol = "cpu_usage value=85.2 1609459200000000000"
    target._send(line_protocol)

    # Verify HTTP call was made correctly
    assert mock_requests.called
    assert mock_requests.call_count == 1

    # Check the request details
    request = mock_requests.last_request
    assert request.url == f"{target.url}?db=test-db"
    assert request.method == "POST"
    assert request.text == line_protocol

    # Check headers
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers["Content-Type"] == "text/plain"


def test_send_http_with_database_param_v2(mock_requests):
    """Test that database parameter is included in URL for InfluxDB2Target"""
    from jot.influxdb import InfluxDB2Target

    target = InfluxDB2Target(endpoint="http://localhost:8086", bucket="test-db", token="test-token")

    mock_requests.post(target.url, status_code=204)

    target._send("test value=1 1609459200000000000")

    # Verify database is in query parameters
    request = mock_requests.last_request
    assert "bucket=test-db" in request.url


def test_send_http_with_database_param_v3(mock_requests):
    """Test that database parameter is included in URL for InfluxDB3Target"""
    from jot.influxdb import InfluxDB3Target

    target = InfluxDB3Target(
        endpoint="http://localhost:8086", database="test-db", token="test-token"
    )

    mock_requests.post(target.url, status_code=204)

    target._send("test value=1 1609459200000000000")

    # Verify database is in query parameters
    request = mock_requests.last_request
    assert "db=test-db" in request.url


def test_send_http_error_handling_4xx(target, mock_requests, capsys):
    """Test HTTP 4xx error handling"""
    # Mock 400 Bad Request
    mock_requests.post(target.url, status_code=400, text="Bad request")

    # Should not raise exception, but print error
    target._send("invalid line protocol")

    # Check that error was printed to stderr
    captured = capsys.readouterr()
    assert "InfluxDB3 error" in captured.err
    assert "400" in captured.err


def test_send_http_error_handling_5xx(target, mock_requests, capsys):
    """Test HTTP 5xx error handling"""
    # Mock 500 Internal Server Error
    mock_requests.post(target.url, status_code=500, text="Internal server error")

    # Should not raise exception, but print error
    target._send("cpu_usage value=85.2 1609459200000000000")

    # Check that error was printed to stderr
    captured = capsys.readouterr()
    assert "InfluxDB3 error" in captured.err
    assert "500" in captured.err


def test_send_http_network_error(target, mock_requests, capsys):
    """Test network error handling"""
    import requests

    # Mock network error
    mock_requests.post(target.url, exc=requests.ConnectionError("Network error"))

    # Should not raise exception, but print error
    target._send("cpu_usage value=85.2 1609459200000000000")

    # Check that error was printed to stderr
    captured = capsys.readouterr()
    assert "InfluxDB3 error" in captured.err
    assert "Network error" in captured.err


def test_send_http_successful_responses(target, mock_requests):
    """Test that successful HTTP responses are handled properly"""
    # Test 204 No Content (typical InfluxDB success response)
    mock_requests.post(target.url, status_code=204)
    target._send("test1 value=1 1609459200000000000")
    assert mock_requests.call_count == 1

    # Test 200 OK (also acceptable)
    mock_requests.post(target.url, status_code=200)
    target._send("test2 value=2 1609459200000000000")
    assert mock_requests.call_count == 2


def test_send_authentication_header(target, mock_requests):
    """Test that authentication header is properly formatted"""
    mock_requests.post(target.url, status_code=204)

    target._send("auth_test value=1 1609459200000000000")

    request = mock_requests.last_request
    auth_header = request.headers.get("Authorization")
    assert auth_header == "Bearer test-token"
    assert auth_header.startswith("Bearer ")


def test_send_content_type_header(target, mock_requests):
    """Test that Content-Type header is set correctly"""
    mock_requests.post(target.url, status_code=204)

    target._send("content_test value=1 1609459200000000000")

    request = mock_requests.last_request
    assert request.headers["Content-Type"] == "text/plain"


def test_magnitude_basic(target, mock_requests, span):
    """Test basic magnitude() method functionality"""
    mock_requests.post(target.url, status_code=204)

    # Test with float value
    target.magnitude("cpu_usage", 85.2, {}, span)

    # Verify HTTP call was made
    assert mock_requests.called
    assert mock_requests.call_count == 1

    # Check the request details
    request = mock_requests.last_request
    assert request.method == "POST"

    # Check line protocol format (should be float without 'i' suffix)
    line_protocol = request.text
    assert "cpu_usage value=85.2" in line_protocol
    assert "85.2i" not in line_protocol  # Should not have integer suffix


def test_magnitude_with_tags(target, mock_requests, sample_tags, span):
    """Test magnitude() with tags"""
    mock_requests.post(target.url, status_code=204)

    target.magnitude("memory_usage", 1024.5, sample_tags, span)

    request = mock_requests.last_request
    line_protocol = request.text

    # Should contain measurement name and value
    assert "memory_usage" in line_protocol
    assert "value=1024.5" in line_protocol

    # Should contain sorted tags
    assert "environment=test" in line_protocol
    assert "host=localhost" in line_protocol
    assert "service=test-app" in line_protocol


def test_magnitude_without_span(target, mock_requests):
    """Test magnitude() without span parameter"""
    mock_requests.post(target.url, status_code=204)

    # Call without span (should work fine)
    target.magnitude("temperature", 23.7, {"sensor": "outdoor"}, None)

    request = mock_requests.last_request
    line_protocol = request.text

    assert "temperature,sensor=outdoor value=23.7" in line_protocol


def test_magnitude_negative_values(target, mock_requests, span):
    """Test magnitude() with negative values"""
    mock_requests.post(target.url, status_code=204)

    target.magnitude("temperature", -10.5, {"location": "freezer"}, span)

    request = mock_requests.last_request
    line_protocol = request.text

    assert "temperature,location=freezer value=-10.5" in line_protocol


def test_magnitude_zero_value(target, mock_requests, span):
    """Test magnitude() with zero value"""
    mock_requests.post(target.url, status_code=204)

    target.magnitude("idle_time", 0.0, {}, span)

    request = mock_requests.last_request
    line_protocol = request.text

    assert "idle_time value=0.0" in line_protocol


def test_magnitude_large_values(target, mock_requests, span):
    """Test magnitude() with large values"""
    mock_requests.post(target.url, status_code=204)

    large_value = 123456789.987654321
    target.magnitude("bytes_transferred", large_value, {"protocol": "https"}, span)

    request = mock_requests.last_request
    line_protocol = request.text

    assert "bytes_transferred,protocol=https" in line_protocol
    assert f"value={large_value}" in line_protocol


def test_magnitude_http_headers(target, mock_requests, span):
    """Test that magnitude() sends correct HTTP headers"""
    mock_requests.post(target.url, status_code=204)

    target.magnitude("cpu_load", 2.5, {}, span)

    request = mock_requests.last_request
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers["Content-Type"] == "text/plain"


def test_magnitude_timestamp_precision(target, mock_requests, span):
    """Test that magnitude() uses nanosecond precision timestamps"""

    mock_requests.post(f"{target.url}/api/v3/write_lp", status_code=204)

    before_ns = time.time_ns()
    target.magnitude("request_time", 150.0, {}, span)
    after_ns = time.time_ns()

    request = mock_requests.last_request
    line_protocol = request.text

    # Extract timestamp from line protocol (last part after space)
    parts = line_protocol.strip().split()
    timestamp_str = parts[-1]
    timestamp_ns = int(timestamp_str)

    # Timestamp should be within reasonable range
    assert before_ns <= timestamp_ns <= after_ns
    # Should be nanosecond precision (19 digits for current epoch)
    assert len(timestamp_str) >= 19


def test_magnitude_error_handling(target, mock_requests, span, capsys):
    """Test that magnitude() handles HTTP errors gracefully"""
    # Mock HTTP error response
    mock_requests.post(target.url, status_code=500, text="Server error")

    # Should not raise exception
    target.magnitude("error_metric", 42.0, {}, span)

    # Should print error to stderr
    captured = capsys.readouterr()
    assert "InfluxDB3 error" in captured.err
    assert "500" in captured.err


def test_count_basic(target, mock_requests, span):
    """Test basic count() method functionality"""
    mock_requests.post(target.url, status_code=204)

    # Test with integer value
    target.count("request_count", 42, {}, span)

    # Verify HTTP call was made
    assert mock_requests.called
    assert mock_requests.call_count == 1

    # Check the request details
    request = mock_requests.last_request
    assert request.method == "POST"

    # Check line protocol format (should be integer with 'i' suffix)
    line_protocol = request.text
    assert "request_count value=42i" in line_protocol
    assert "value=42 " not in line_protocol  # Should not be without suffix


def test_count_with_tags(target, mock_requests, sample_tags, span):
    """Test count() with tags"""
    mock_requests.post(target.url, status_code=204)

    target.count("error_count", 5, sample_tags, span)

    request = mock_requests.last_request
    line_protocol = request.text

    # Should contain measurement name and value with integer suffix
    assert "error_count" in line_protocol
    assert "value=5i" in line_protocol

    # Should contain sorted tags
    assert "environment=test" in line_protocol
    assert "host=localhost" in line_protocol
    assert "service=test-app" in line_protocol


def test_count_without_span(target, mock_requests):
    """Test count() without span parameter"""
    mock_requests.post(target.url, status_code=204)

    # Call without span (should work fine)
    target.count("page_views", 150, {"endpoint": "/api"}, None)

    request = mock_requests.last_request
    line_protocol = request.text

    assert "page_views,endpoint=/api value=150i" in line_protocol


def test_count_zero_value(target, mock_requests, span):
    """Test count() with zero value"""
    mock_requests.post(target.url, status_code=204)

    target.count("failed_requests", 0, {}, span)

    request = mock_requests.last_request
    line_protocol = request.text

    assert "failed_requests value=0i" in line_protocol


def test_count_large_values(target, mock_requests, span):
    """Test count() with large values"""
    mock_requests.post(target.url, status_code=204)

    large_value = 9223372036854775807  # Max int64
    target.count("total_bytes", large_value, {"protocol": "tcp"}, span)

    request = mock_requests.last_request
    line_protocol = request.text

    assert "total_bytes,protocol=tcp" in line_protocol
    assert f"value={large_value}i" in line_protocol


def test_count_http_headers(target, mock_requests, span):
    """Test that count() sends correct HTTP headers"""
    mock_requests.post(target.url, status_code=204)

    target.count("user_logins", 1, {}, span)

    request = mock_requests.last_request
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers["Content-Type"] == "text/plain"


def test_count_timestamp_precision(target, mock_requests, span):
    """Test that count() uses nanosecond precision timestamps"""

    mock_requests.post(f"{target.url}/api/v3/write_lp", status_code=204)

    before_ns = time.time_ns()
    target.count("events", 1, {}, span)
    after_ns = time.time_ns()

    request = mock_requests.last_request
    line_protocol = request.text

    # Extract timestamp from line protocol (last part after space)
    parts = line_protocol.strip().split()
    timestamp_str = parts[-1]
    timestamp_ns = int(timestamp_str)

    # Timestamp should be within reasonable range
    assert before_ns <= timestamp_ns <= after_ns
    # Should be nanosecond precision (19 digits for current epoch)
    assert len(timestamp_str) >= 19


def test_count_integer_suffix_required(target, mock_requests, span):
    """Test that count() always adds 'i' suffix for integer values"""
    mock_requests.post(f"{target.url}/api/v3/write_lp", status_code=204)

    # Test various integer values
    test_cases = [1, 0, -1, 42, 1000000]

    for value in test_cases:
        target.count("test_metric", value, {"case": str(value)}, span)

        request = mock_requests.last_request
        line_protocol = request.text

        # Should always have 'i' suffix
        assert f"value={value}i" in line_protocol
        # Should not have value without suffix
        assert f"value={value} " not in line_protocol


def test_count_vs_magnitude_field_types(target, mock_requests, span):
    """Test that count() uses integer format while magnitude() uses float format"""
    mock_requests.post(f"{target.url}/api/v3/write_lp", status_code=204)

    # Test count (should have 'i' suffix)
    target.count("counter", 42, {}, span)
    request = mock_requests.last_request
    line_protocol = request.text
    assert "value=42i" in line_protocol

    # Test magnitude (should not have 'i' suffix)
    target.magnitude("gauge", 42.0, {}, span)
    request = mock_requests.last_request
    line_protocol = request.text
    assert "value=42.0" in line_protocol
    assert "42.0i" not in line_protocol


def test_count_error_handling(target, mock_requests, span, capsys):
    """Test that count() handles HTTP errors gracefully"""
    # Mock HTTP error response
    mock_requests.post(target.url, status_code=500, text="Server error")

    # Should not raise exception
    target.count("error_counter", 1, {}, span)

    # Should print error to stderr
    captured = capsys.readouterr()
    assert "InfluxDB3 error" in captured.err
    assert "500" in captured.err


def test_log_method_is_noop(target, mock_requests, span):
    """Test that log() method does nothing (no HTTP calls)"""
    mock_requests.post(f"{target.url}/api/v3/write_lp", status_code=204)

    # Call log method
    target.log(1, "Test log message", {"key": "value"}, span)

    # Should not make any HTTP calls
    assert not mock_requests.called
    assert mock_requests.call_count == 0


def test_error_method_is_noop(target, mock_requests, span):
    """Test that error() method does nothing (no HTTP calls)"""
    mock_requests.post(f"{target.url}/api/v3/write_lp", status_code=204)

    # Call error method
    exception = Exception("Test exception")
    target.error("Test error message", exception, {"key": "value"}, span)

    # Should not make any HTTP calls
    assert not mock_requests.called
    assert mock_requests.call_count == 0


def test_start_method_is_noop(target, mock_requests, span):
    """Test that start() method does nothing (no HTTP calls)"""
    mock_requests.post(f"{target.url}/api/v3/write_lp", status_code=204)

    # Call start method
    target.start({"key": "value"}, span)

    # Should not make any HTTP calls
    assert not mock_requests.called
    assert mock_requests.call_count == 0


def test_finish_method_is_noop(target, mock_requests, span):
    """Test that finish() method does nothing (no HTTP calls)"""
    mock_requests.post(f"{target.url}/api/v3/write_lp", status_code=204)

    # Call finish method
    target.finish({"key": "value"}, span)

    # Should not make any HTTP calls
    assert not mock_requests.called
    assert mock_requests.call_count == 0


def test_event_method_is_noop(target, mock_requests, span):
    """Test that event() method does nothing (no HTTP calls)"""
    mock_requests.post(f"{target.url}/api/v3/write_lp", status_code=204)

    # Call event method
    target.event("Test event", {"key": "value"}, span)

    # Should not make any HTTP calls
    assert not mock_requests.called
    assert mock_requests.call_count == 0


def test_all_noop_methods_together(target, mock_requests, span):
    """Test that all non-metric methods together make no HTTP calls"""
    mock_requests.post(f"{target.url}/api/v3/write_lp", status_code=204)

    # Call all non-metric methods
    target.log(1, "Log message", {"log": "tag"}, span)
    target.error("Error message", Exception("test"), {"error": "tag"}, span)
    target.start({"start": "tag"}, span)
    target.finish({"finish": "tag"}, span)
    target.event("Event name", {"event": "tag"}, span)

    # Should not make any HTTP calls despite multiple method calls
    assert not mock_requests.called
    assert mock_requests.call_count == 0


def test_noop_methods_vs_metric_methods(target, mock_requests, span):
    """Test that non-metric methods are no-ops while metric methods work"""
    mock_requests.post(f"{target.url}/api/v3/write_lp", status_code=204)

    # Call non-metric methods (should be no-ops)
    target.log(1, "Log message", {}, span)
    target.error("Error", Exception("test"), {}, span)
    target.start({}, span)
    target.finish({}, span)
    target.event("Event", {}, span)

    # Should not have made any HTTP calls yet
    assert not mock_requests.called
    assert mock_requests.call_count == 0

    # Now call a metric method (should make HTTP call)
    target.magnitude("test_metric", 42.0, {}, span)

    # Should have made exactly one HTTP call
    assert mock_requests.called
    assert mock_requests.call_count == 1

    # Verify it was the metric call
    request = mock_requests.last_request
    assert "test_metric" in request.text
    assert "value=42.0" in request.text
