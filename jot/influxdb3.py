import requests
import time
import traceback

from .base import Target


class InfluxDB3Target(Target):
    """Target for sending metrics to InfluxDB 3.0 using line protocol"""

    @classmethod
    def default(cls, level=None):
        return cls(
            url="http://localhost:8086",
            token="",
            database="default",
            level=level
        )

    def __init__(self, url, token, database, level=None):
        super().__init__(level=level)
        self.url = url
        self.token = token
        self.database = database
        self.session = requests.Session()

    def magnitude(self, name, value, tags, span=None):
        """Send a gauge metric (magnitude) to InfluxDB"""
        # Get current timestamp in nanoseconds
        timestamp_ns = time.time_ns()
        
        # Format as line protocol
        line_protocol = self._format_line_protocol(name, value, tags, timestamp_ns)
        
        # Send to InfluxDB
        self._send(line_protocol)

    def count(self, name, value, tags, span=None):
        """Send a counter metric (count) to InfluxDB"""
        # Get current timestamp in nanoseconds
        timestamp_ns = time.time_ns()
        
        # Format as line protocol with integer value
        line_protocol = self._format_line_protocol(name, value, tags, timestamp_ns)
        
        # Send to InfluxDB
        self._send(line_protocol)

    def _format_line_protocol(self, measurement, value, tags, timestamp_ns):
        """Format a metric in InfluxDB line protocol format
        
        Format: measurement,tag_key=tag_value field_key=field_value timestamp_ns
        """
        # Escape measurement name
        escaped_measurement = self._escape_measurement(measurement)
        
        # Format tags (sorted for consistency)
        tag_string = ""
        if tags:
            sorted_tags = sorted(tags.items())
            escaped_tags = [f"{self._escape_tag_key(k)}={self._escape_tag_value(v)}" for k, v in sorted_tags]
            tag_string = "," + ",".join(escaped_tags)
        
        # Format field value with proper type suffix
        if isinstance(value, int):
            field_value = f"{value}i"
        else:
            field_value = str(value)
        
        # Construct line protocol string
        return f"{escaped_measurement}{tag_string} value={field_value} {timestamp_ns}"
    
    def _escape_measurement(self, measurement):
        """Escape measurement name for line protocol"""
        return measurement.replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")
    
    def _escape_tag_key(self, tag_key):
        """Escape tag key for line protocol"""
        return str(tag_key).replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")
    
    def _escape_tag_value(self, tag_value):
        """Escape tag value for line protocol"""
        return str(tag_value).replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")
    
    def _send(self, line_protocol):
        """Send line protocol data to InfluxDB via HTTP"""
        try:
            # Construct URL with database parameter
            url = f"{self.url}/api/v3/write_lp"
            params = {"db": self.database}
            
            # Set headers
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "text/plain"
            }
            
            # Send HTTP request
            response = self.session.post(url, params=params, headers=headers, data=line_protocol)
            
            # Check for HTTP errors
            if response.status_code >= 400:
                print(f"InfluxDB3 error: HTTP {response.status_code} - {response.text}", file=traceback.sys.stderr)
                
        except Exception as e:
            # Handle network errors and other exceptions gracefully
            print(f"InfluxDB3 error: {str(e)}", file=traceback.sys.stderr)