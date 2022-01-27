import os
import traceback
from time import time_ns
import json

import requests

from .base import Span, Target


class ZipkinAttribute:
    def __init__(self, value, timestamp=None):
        self.value = value
        self.timestamp = timestamp if timestamp is not None else time_ns() // 1000


class ZipkinSpan(Span):
    def __init__(self, trace_id, parent_id, id, name=None):
        super().__init__(trace_id, parent_id, id, name)
        self.attributes = []


class ZipkinTarget(Target):
    """A target that sends traces to a zipkin server"""

    _span_class = ZipkinSpan

    @classmethod
    def _gen_id(cls):
        return os.urandom(8).hex()

    def __init__(self, url):
        self.url = url
        self.session = requests.Session()

    def _send(self, payload):

        # FIXME: remove debugging code
        print(json.dumps(payload))

        try:
            response = self.session.post(self.url, json=payload)
            if response.status_code > 299:
                print(f"Zipkin response status code: {response.status_code}")
                print(response.text)
        except Exception:
            # TODO: implement a better error handling mechanism
            print(traceback.format_exc())

    def finish(self, tags, span):
        obj = {
            "traceId": span.trace_id,
            "parentId": span.parent_id,
            "id": span.id,
            "timestamp": span.start_time // 1000,
            "duration": span.duration,
        }

        _set_attr(obj, "name", span.name)

        _set_tag(obj, tags, "kind")
        _set_tag(obj, tags, "shared")
        _set_tag(obj, tags, "localEndpoint")
        _set_tag(obj, tags, "remoteEndpoint")
        obj["tags"] = tags

        annotations = [{"timestamp": a.timestamp, "value": a.value} for a in span.attributes]
        if len(annotations) > 0:
            obj["annotations"] = annotations

        payload = [obj]
        self._send(payload)

    def event(self, name, tags, span=None):
        if span is not None:
            span.attributes.append(ZipkinAttribute(name))


def _set_attr(payload, name, value):
    if value is not None:
        payload[name] = value


def _set_tag(payload, tags, name):
    if name in tags:
        payload[name] = tags.pop(name)
