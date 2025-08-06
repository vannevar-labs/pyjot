from jot.influxdb import InfluxDB2Target, InfluxDB3Target


def test_from_environment_v2_with_all_env_vars(monkeypatch):
    """Test InfluxDB2Target.from_environment with all environment variables set"""
    monkeypatch.setenv("JOT_INFLUXDB2_ENDPOINT", "http://influx-env:8086")
    monkeypatch.setenv("JOT_INFLUXDB2_BUCKET", "env-bucket")
    monkeypatch.setenv("JOT_INFLUXDB2_TOKEN", "env-token")
    monkeypatch.setenv("JOT_INFLUXDB2_ORG", "env-org")

    target = InfluxDB2Target.from_environment()

    assert target is not None
    assert target.url == "http://influx-env:8086/api/v2/write"
    assert target.params == {"bucket": "env-bucket", "org": "env-org"}
    assert target.headers == {"Content-Type": "text/plain", "Authorization": "Bearer env-token"}


def test_from_environment_v2_with_minimum_env_vars(monkeypatch):
    """Test InfluxDB2Target.from_environment with minimum required environment variables"""
    monkeypatch.setenv("JOT_INFLUXDB2_ENDPOINT", "http://influx-env:8086")
    monkeypatch.setenv("JOT_INFLUXDB2_BUCKET", "env-bucket")
    monkeypatch.delenv("JOT_INFLUXDB2_TOKEN", raising=False)
    monkeypatch.delenv("JOT_INFLUXDB2_ORG", raising=False)

    target = InfluxDB2Target.from_environment()

    assert target is not None
    assert target.url == "http://influx-env:8086/api/v2/write"
    assert target.params == {"bucket": "env-bucket"}
    assert "Authorization" not in target.headers


def test_from_environment_v2_without_required_env_vars(monkeypatch):
    """Test InfluxDB2Target.from_environment with missing required environment variables"""
    # Clear any existing environment variables
    for var in [
        "JOT_INFLUXDB2_ENDPOINT",
        "INFLUXDB2_ENDPOINT",
        "JOT_INFLUXDB2_BUCKET",
        "INFLUXDB2_BUCKET",
    ]:
        monkeypatch.delenv(var, raising=False)

    target = InfluxDB2Target.from_environment()
    assert target is None


def test_from_environment_v2_with_non_prefixed_vars(monkeypatch):
    """Test InfluxDB2Target.from_environment with non-prefixed environment variables"""
    monkeypatch.setenv("INFLUXDB2_ENDPOINT", "http://influx-env:8086")
    monkeypatch.setenv("INFLUXDB2_BUCKET", "env-bucket")
    monkeypatch.setenv("INFLUXDB2_TOKEN", "env-token")

    target = InfluxDB2Target.from_environment()

    assert target is not None
    assert target.url == "http://influx-env:8086/api/v2/write"
    assert target.params == {"bucket": "env-bucket"}
    assert target.headers == {"Content-Type": "text/plain", "Authorization": "Bearer env-token"}


def test_from_environment_v3_with_all_env_vars(monkeypatch):
    """Test InfluxDB3Target.from_environment with all environment variables set"""
    monkeypatch.setenv("JOT_INFLUXDB3_ENDPOINT", "http://influx-env:8086")
    monkeypatch.setenv("JOT_INFLUXDB3_DATABASE", "env-database")
    monkeypatch.setenv("JOT_INFLUXDB3_TOKEN", "env-token")

    target = InfluxDB3Target.from_environment()

    assert target is not None
    assert target.url == "http://influx-env:8086/api/v3/write_lp"
    assert target.params == {"db": "env-database"}
    assert target.headers == {"Content-Type": "text/plain", "Authorization": "Bearer env-token"}


def test_from_environment_v3_with_minimum_env_vars(monkeypatch):
    """Test InfluxDB3Target.from_environment with minimum required environment variables"""
    monkeypatch.setenv("JOT_INFLUXDB3_ENDPOINT", "http://influx-env:8086")
    monkeypatch.setenv("JOT_INFLUXDB3_DATABASE", "env-database")
    monkeypatch.delenv("JOT_INFLUXDB3_TOKEN", raising=False)

    target = InfluxDB3Target.from_environment()

    assert target is not None
    assert target.url == "http://influx-env:8086/api/v3/write_lp"
    assert target.params == {"db": "env-database"}
    assert "Authorization" not in target.headers


def test_from_environment_v3_without_required_env_vars(monkeypatch):
    """Test InfluxDB3Target.from_environment with missing required environment variables"""
    # Clear any existing environment variables
    for var in [
        "JOT_INFLUXDB3_ENDPOINT",
        "INFLUXDB3_ENDPOINT",
        "JOT_INFLUXDB3_DATABASE",
        "INFLUXDB3_DATABASE",
    ]:
        monkeypatch.delenv(var, raising=False)

    target = InfluxDB3Target.from_environment()
    assert target is None


def test_from_environment_v3_with_non_prefixed_vars(monkeypatch):
    """Test InfluxDB3Target.from_environment with non-prefixed environment variables"""
    monkeypatch.setenv("INFLUXDB3_ENDPOINT", "http://influx-env:8086")
    monkeypatch.setenv("INFLUXDB3_DATABASE", "env-database")
    monkeypatch.setenv("INFLUXDB3_TOKEN", "env-token")

    target = InfluxDB3Target.from_environment()

    assert target is not None
    assert target.url == "http://influx-env:8086/api/v3/write_lp"
    assert target.params == {"db": "env-database"}
    assert target.headers == {"Content-Type": "text/plain", "Authorization": "Bearer env-token"}
