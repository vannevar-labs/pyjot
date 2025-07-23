import traceback

import requests

from jot import util
from jot.base import Target


class ZipkinTarget(Target):
    """A target that sends traces to a zipkin server"""

    @classmethod
    def from_environment(cls):
        url = util.get_env("ZIPKIN_URL")
        if url:
            return cls(url)

    def __init__(self, url, level=None):
        super().__init__(level)
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
            "traceId": util.format_trace_id(span.trace_id),
            "parentId": util.format_span_id(span.parent_id) if span.parent_id is not None else None,
            "id": util.format_span_id(span.id),
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
