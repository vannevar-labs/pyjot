import pytest
from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    Summary,
    make_wsgi_app,
)
from prometheus_client.parser import text_string_to_metric_families

from jot.base import Span
from jot.prometheus import PrometheusTarget
from jot.util import generate_span_id, generate_trace_id


def start_response(status, headers):
    pass


@pytest.fixture(autouse=True)
def reset_registry():
    collectors = list(REGISTRY._collector_to_names.keys())
    for c in collectors:
        REGISTRY.unregister(c)


@pytest.fixture()
def app():
    return make_wsgi_app()


@pytest.fixture
def target():
    return PrometheusTarget(level=0, port=None)


@pytest.fixture
def get_content(app):
    def get_content():
        environment = {"REQUEST_METHOD": "GET", "PATH_INFO": "/metrics"}
        buf_it = app(environment, start_response)
        return "".join(buf.decode("utf-8") for buf in buf_it)

    return get_content


@pytest.fixture
def get_samples(get_content):
    def get_samples(name):
        content = get_content()
        samples = []
        for family in text_string_to_metric_families(content):
            for sample in family.samples:
                if sample.name == name:
                    samples.append(sample)
        return samples

    return get_samples


def test_auto_magnitude(target, get_samples):
    target.magnitude("auto_magnitude", 42, {"nork": "pliff"}, None)
    samples = get_samples("auto_magnitude")
    assert len(samples) == 1
    s = samples[0]
    assert s.labels == {"nork": "pliff"}
    assert s.value == 42


def test_auto_count(target, get_samples):
    target.magnitude("auto_count", 42, {"nork": "pliff"}, None)
    samples = get_samples("auto_count")
    assert len(samples) == 1
    s = samples[0]
    assert s.labels == {"nork": "pliff"}
    assert s.value == 42


def test_auto_count_twice(target, get_samples):
    target.count("auto_count", 3, {"nork": "pliff"}, None)
    target.count("auto_count", 5, {"nork": "pliff"}, None)
    samples = get_samples("auto_count_total")
    assert len(samples) == 1
    s = samples[0]
    assert s.labels == {"nork": "pliff"}
    assert s.value == 8


def test_auto_count_two_labels(target, get_samples):
    target.count("auto_count", 3, {"nork": "pliff"}, None)
    target.count("auto_count", 5, {"nork": "ork"}, None)
    samples = get_samples("auto_count_total")
    assert len(samples) == 2

    s = samples[0]
    assert s.labels == {"nork": "pliff"}
    assert s.value == 3

    s = samples[1]
    assert s.labels == {"nork": "ork"}
    assert s.value == 5


def test_auto_count_two_labels_twice(target, get_samples):
    target.count("auto_count", 3, {"nork": "pliff"}, None)
    target.count("auto_count", 5, {"nork": "pliff"}, None)
    target.count("auto_count", 7, {"nork": "ork"}, None)
    target.count("auto_count", 11, {"nork": "ork"}, None)
    samples = get_samples("auto_count_total")
    assert len(samples) == 2

    s = samples[0]
    assert s.labels == {"nork": "pliff"}
    assert s.value == 8

    s = samples[1]
    assert s.labels == {"nork": "ork"}
    assert s.value == 18


def test_prefab_count(target, get_samples):
    target.add_metric(Counter("prefab_count", "A prefab count metric", ["nork"]))
    target.count("prefab_count", 3, {"nork": "pliff"}, None)
    target.count("prefab_count", 5, {"nork": "pliff"}, None)
    samples = get_samples("prefab_count_total")
    assert len(samples) == 1
    s = samples[0]
    assert s.labels == {"nork": "pliff"}
    assert s.value == 8


def test_prefab_magnitude(target, get_samples):
    target.add_metric(Gauge("prefab_gauge", "A prefab gauge metric", ["nork"]))
    target.magnitude("prefab_gauge", 3, {"nork": "pliff"}, None)
    target.magnitude("prefab_gauge", 5, {"nork": "pliff"}, None)
    samples = get_samples("prefab_gauge")
    assert len(samples) == 1
    s = samples[0]
    assert s.labels == {"nork": "pliff"}
    assert s.value == 5.0


def test_prefab_summary(target, get_samples, get_content):
    target.add_metric(Summary("prefab_summary", "A prefab summary metric", ["nork"]))
    target.magnitude("prefab_summary", 3, {"nork": "pliff"}, None)
    target.magnitude("prefab_summary", 5, {"nork": "pliff"}, None)

    samples = get_samples("prefab_summary_count")
    assert len(samples) == 1
    s = samples[0]
    assert s.labels == {"nork": "pliff"}
    assert s.value == 2

    samples = get_samples("prefab_summary_sum")
    assert len(samples) == 1
    s = samples[0]
    assert s.labels == {"nork": "pliff"}
    assert s.value == 8.0


def test_prefab_histogram(target, get_samples, get_content):
    target.add_metric(Histogram("prefab_histogram", "A prefab histogram metric", ["nork"]))
    target.magnitude("prefab_histogram", 3, {"nork": "pliff"}, None)
    target.magnitude("prefab_histogram", 5, {"nork": "pliff"}, None)

    samples = get_samples("prefab_histogram_bucket")
    assert len(samples) == 15
    for s in samples:
        assert s.labels["nork"] == "pliff"
        assert "le" in s.labels
        assert s.value in [0.0, 2.0]

    samples = get_samples("prefab_histogram_count")
    assert len(samples) == 1
    s = samples[0]
    assert s.labels == {"nork": "pliff"}
    assert s.value == 2

    samples = get_samples("prefab_histogram_sum")
    assert len(samples) == 1
    s = samples[0]
    assert s.labels == {"nork": "pliff"}
    assert s.value == 8.0


def test_count_with_span(target, get_samples):
    trace_id = generate_trace_id()
    span_id = generate_span_id()
    span = Span(trace_id, None, span_id, "test_span")
    target.count("span_count", 42, {"nork": "pliff"}, span)

    samples = get_samples("span_count_total")
    assert len(samples) == 1
    s = samples[0]
    assert s.labels == {"nork": "pliff"}
