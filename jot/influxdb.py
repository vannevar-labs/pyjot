import sys
import time

import requests

from .base import Target


class InfluxLineProtocolTarget(Target):
    """Abstract base class for InfluxDB line protocol targets."""

    def __init__(self, url, params, headers, level=None):
        super().__init__(level=level)
        self.url = url
        self.params = params
        self.headers = headers
        self.session = requests.Session()

    def magnitude(self, name, value, tags, span=None):
        timestamp_ns = time.time_ns()
        line_protocol = self._format_line_protocol(name, value, tags, timestamp_ns)
        self._send(line_protocol)

    def count(self, name, value, tags, span=None):
        timestamp_ns = time.time_ns()
        line_protocol = self._format_line_protocol(name, value, tags, timestamp_ns)
        self._send(line_protocol)

    def _url_from_endpoint(self, endpoint):
        return endpoint

    def _params_from_database(self, database):
        return {}

    def _headers_from_token(self, token):
        headers = {"Content-Type": "text/plain"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _format_line_protocol(self, measurement, value, tags, timestamp_ns):
        """Format: measurement,tag_key=tag_value field_key=field_value timestamp_ns"""
        # Escape measurement name
        escaped_measurement = self._escape_measurement(measurement)

        # Format tags (sorted for consistency)
        tag_string = ""
        if tags:
            sorted_tags = sorted(tags.items())
            escaped_tags = [
                f"{self._escape_tag_key(k)}={self._escape_tag_value(v)}" for k, v in sorted_tags
            ]
            tag_string = "," + ",".join(escaped_tags)

        # Format field value with proper type suffix
        if isinstance(value, int):
            field_value = f"{value}i"
        else:
            field_value = str(value)

        # Construct line protocol string
        return f"{escaped_measurement}{tag_string} value={field_value} {timestamp_ns}"

    def _escape_measurement(self, measurement):
        return measurement.replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

    def _escape_tag_key(self, tag_key):
        return str(tag_key).replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

    def _escape_tag_value(self, tag_value):
        return str(tag_value).replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

    def _send(self, line_protocol):
        try:
            # Send HTTP request
            response = self.session.post(
                self.url, params=self.params, headers=self.headers, data=line_protocol
            )

            # Check for HTTP errors
            if response.status_code >= 400:
                print(
                    f"InfluxDB3 error: HTTP {response.status_code} - {response.text}",
                    file=sys.stderr,
                )

        except Exception as e:
            # Handle network errors and other exceptions gracefully
            print(f"InfluxDB3 error: {str(e)}", file=sys.stderr)


class InfluxDB2Target(InfluxLineProtocolTarget):
    @classmethod
    def default(cls, level=None):
        return cls(endpoint="http://localhost:8086", bucket="default", level=level)

    def __init__(self, endpoint, bucket, token=None, org=None, level=None):
        url = f"{endpoint}/api/v2/write"
        params = {"bucket": bucket}
        if org:
            params["org"] = org
        headers = self._headers_from_token(token)
        super().__init__(url=url, params=params, headers=headers, level=level)


class InfluxDB3Target(InfluxLineProtocolTarget):
    @classmethod
    def default(cls, level=None):
        return cls(endpoint="http://localhost:8086", database="default", level=level)

    def __init__(self, endpoint, database, token=None, level=None):
        url = f"{endpoint}/api/v3/write_lp"
        params = {"db": database}
        headers = self._headers_from_token(token)
        super().__init__(url=url, params=params, headers=headers, level=level)
