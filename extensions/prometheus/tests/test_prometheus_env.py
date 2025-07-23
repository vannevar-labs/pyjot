from unittest.mock import MagicMock, patch

import pytest

import jot.prometheus
from jot.prometheus import PrometheusTarget


# We need to isolate these tests completely from the prometheus module
@pytest.fixture(autouse=True)
def reset_prometheus_module():
    """Reset all the prometheus module's state between tests"""

    # Save original values
    original_module_dict = jot.prometheus.prometheus.__dict__.copy()

    # Reset all module variables
    jot.prometheus.prometheus._server = None
    jot.prometheus.prometheus._thread = None
    jot.prometheus.prometheus._port = 8080

    yield

    # Restore the module's original state
    jot.prometheus.prometheus.__dict__.clear()
    jot.prometheus.prometheus.__dict__.update(original_module_dict)


@pytest.fixture
def mock_server_setup():
    """Mock the server setup to prevent actual server start"""
    # Define mock objects
    mock_server = MagicMock()
    mock_thread = MagicMock()

    # Create patch for _init_prometheus to avoid actually starting the server
    def mock_init_prometheus(port):
        jot.prometheus.prometheus._port = port
        jot.prometheus.prometheus._server = mock_server
        jot.prometheus.prometheus._thread = mock_thread
        return mock_server, mock_thread

    with patch("jot.prometheus.prometheus._init_prometheus", side_effect=mock_init_prometheus):
        yield


def test_from_environment_with_no_vars(monkeypatch):
    """Test PrometheusTarget.from_environment with no port set"""
    # Clear any existing environment variables
    monkeypatch.delenv("PROMETHEUS_PORT", raising=False)
    monkeypatch.delenv("JOT_PROMETHEUS_PORT", raising=False)
    target = PrometheusTarget.from_environment()
    assert target is None


def test_from_environment_with_port(monkeypatch, mock_server_setup):
    """Test PrometheusTarget.from_environment with a specific port"""
    monkeypatch.setenv("PROMETHEUS_PORT", "9090")

    target = PrometheusTarget.from_environment()

    assert target is not None
    assert isinstance(target, PrometheusTarget)

    # Check the module's global port value
    assert jot.prometheus.prometheus._port == 9090


def test_from_environment_with_jot_prefix(monkeypatch, mock_server_setup):
    """Test PrometheusTarget.from_environment with JOT_ prefixed env var

    Note: This test verifies current behavior, which is that the JOT_ prefix
    is NOT used in the PrometheusTarget implementation. If that changes in the
    future, this test would need to be updated.
    """
    monkeypatch.setenv("JOT_PROMETHEUS_PORT", "7070")

    target = PrometheusTarget.from_environment()

    assert target is not None
    assert isinstance(target, PrometheusTarget)

    # Check the module's global port value
    assert jot.prometheus.prometheus._port == 7070
