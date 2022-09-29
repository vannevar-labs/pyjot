import traceback
from time import time_ns
import json

import requests
from .base import Target


class ZipkinTarget(Target):
    """A target that sends traces to a zipkin server"""

    def __init__(self, url):
        self.url = url
        self.session = requests.Session()

    def _send(self, payload):
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
            "traceId": span.trace_id_hex,
            "parentId": span.parent_id_hex,
            "id": span.id_hex,
            "timestamp": span.start_time // 1000,
            "duration": span.duration // 1000,
        }

        _set_attr(obj, "name", span.name)

        _set_tag(obj, tags, "kind")
        _set_tag(obj, tags, "shared")
        _set_tag(obj, tags, "localEndpoint")
        _set_tag(obj, tags, "remoteEndpoint")
        obj["tags"] = tags

        annotations = [{"timestamp": a.timestamp, "value": a.name} for a in span.events]
        if len(annotations) > 0:
            obj["annotations"] = annotations

        payload = [obj]
        self._send(payload)


def _set_attr(payload, name, value):
    if value is not None:
        payload[name] = value


def _set_tag(payload, tags, name):
    if name in tags:
        payload[name] = tags.pop(name)
