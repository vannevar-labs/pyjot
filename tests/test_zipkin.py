from jot.zipkin import ZipkinTarget
import sys
import os

HEX_ALPHABET = "0123456789abcdef"


def check_id(id):
    assert type(id) == str
    assert len(id) == 16
    for c in id:
        assert c in HEX_ALPHABET


def test_constructor():
    ZipkinTarget(None)


def test_start_root():
    target = ZipkinTarget(None)
    span = target.start()
    check_id(span.trace_id)
    check_id(span.id)
    assert span.parent_id is None
    assert span.name is None


def test_start_child():
    target = ZipkinTarget(None)
    root = target.start()
    span = target.start(root)
    check_id(span.trace_id)
    check_id(span.id)
    assert span.parent_id == root.id


def test_start_name():
    target = ZipkinTarget(None)
    span = target.start(None, "root span")
    assert span.name == "root span"


def test_finish(requests_mock):
    target = ZipkinTarget("http://example.com/post")
    root = target.start()
    span = target.start(root, "test-span")
    target.event(span, "an event", {})
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
    target.finish(span, tags)
    assert requests_mock.called
