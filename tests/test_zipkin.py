import json

import pytest

from jot.base import Span
from jot.zipkin import ZipkinTarget


@pytest.fixture
def span():
    span = Span()
    span.start()
    return span


def test_constructor():
    ZipkinTarget(None)


def test_finish(span, requests_mock):
    child = Span(trace_id=span.trace_id, parent_id=span.id, name="test-span")
    child.start()
    target = ZipkinTarget("http://example.com/post")
    target.event("an event", {}, child)
    tags = {
        "pluff": 667,
        "kind": "CLIENT",
        "shared": True,
        "localEndpoint": {
            "ipv4": "192.168.1.51",
        },
        "remoteEndpoint": {"serviceName": "postgres", "ipv4": "192.168.1.1", "port": 5432},
    }

    requests_mock.post(target.url, status_code=202)
    target.finish(tags, child)
    assert requests_mock.called_once

    payload = json.loads(requests_mock.last_request.text)

    assert isinstance(payload, list)
    assert len(payload) == 1
    s = payload[0]

    assert_is_id(s, "id")
    assert_is_id(s, "traceId", 32)
    assert_is_id(s, "parentId")
    assert_is_int(s, "timestamp")
    assert_is_int(s, "duration")

    assert s["name"] == "test-span"
    assert s["kind"] == "CLIENT"
    assert s["shared"] is True
    assert s["tags"] == {"pluff": 667}
    assert s["localEndpoint"] == {"ipv4": "192.168.1.51"}
    assert s["remoteEndpoint"] == {"serviceName": "postgres", "ipv4": "192.168.1.1", "port": 5432}

    assert sorted(s.keys()) == [
        "annotations",
        "duration",
        "id",
        "kind",
        "localEndpoint",
        "name",
        "parentId",
        "remoteEndpoint",
        "shared",
        "tags",
        "timestamp",
        "traceId",
    ]


def test_root_span(span, requests_mock):
    target = ZipkinTarget("http://example.com/post")
    requests_mock.post(target.url, status_code=202)
    target.finish({}, span)
    assert requests_mock.called_once

    span = json.loads(requests_mock.last_request.text)[0]
    assert "parentId" in span
    assert span["parentId"] is None


def assert_is_id(obj, name, expected_len=16):
    assert name in obj
    assert isinstance(obj[name], str)
    assert len(obj[name]) == expected_len


def assert_is_int(obj, name):
    assert name in obj
    assert isinstance(obj[name], int)


def check_ids(span):
    assert isinstance(span.trace_id, bytes)
    assert len(span.trace_id) == 16
    assert isinstance(span.id, bytes)
    assert len(span.id) == 8
    if span.parent_id is not None:
        assert isinstance(span.parent_id, bytes)
        assert len(span.parent_id) == 8
