from jot.zipkin import ZipkinTarget
import json


def test_constructor():
    ZipkinTarget(None)


def test_start_root():
    target = ZipkinTarget(None)
    span = target.start()
    check_ids(span)
    assert span.parent_id is None
    assert span.name is None


def test_start_child():
    target = ZipkinTarget(None)
    root = target.start()
    span = target.start(root.trace_id, root.id, name="span")
    check_ids(span)
    assert span.parent_id == root.id


def test_start_name():
    target = ZipkinTarget(None)
    span = target.start(name="root span")
    assert span.name == "root span"


def test_finish(requests_mock):
    target = ZipkinTarget("http://example.com/post")
    root = target.start()
    span = target.start(root.trace_id, root.id, name="test-span")
    target.event("an event", {}, span)
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
    target.finish(tags, span)
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


def test_root_span(requests_mock):
    target = ZipkinTarget("http://example.com/post")
    root = target.start()

    requests_mock.post(target.url, status_code=202)
    target.finish({}, root)
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
