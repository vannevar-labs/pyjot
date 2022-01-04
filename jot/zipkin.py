import os
import traceback
from time import time_ns

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

    @classmethod
    def _gen_id(cls):
        return os.urandom(8).hex()

    def __init__(self, url):
        self.url = url
        self.session = requests.Session()

    def _start(self, trace_id, parent_id, id, name):
        return ZipkinSpan(trace_id, parent_id, id, name)

    def _send(self, payload):
        try:
            response = self.session.post(self.url, json=payload)
            response.raise_for_status()
        except Exception:
            # TODO: implement a better error handling mechanism
            print(traceback.format_exc())


    def finish(self, span, tags):
        payload = {
            "traceId": span.trace_id,
            "id": span.id,
            "timestamp": span.start_time // 1000,
            "duration": span.duration,
        }

        _set_attr(payload, "parentId", span.parent_id)
        _set_attr(payload, "name", span.name)

        _set_tag(payload, tags, "kind")
        _set_tag(payload, tags, "shared")
        _set_tag(payload, tags, "localEndpoint")
        _set_tag(payload, tags, "remoteEndpoint")
        payload["tags"] = tags

        annotations = [{"timestamp": a.timestamp, "value": a.value} for a in span.attributes]
        if len(annotations) > 0:
            payload["annotations"] = annotations

        self._send(payload)

    def event(self, span, name, tags):
        span.attributes.append(ZipkinAttribute(name))


def _set_attr(payload, name, value):
    if value is not None:
        payload[name] = value


def _set_tag(payload, tags, name):
    if name in tags:
        payload[name] = tags.pop(name)
