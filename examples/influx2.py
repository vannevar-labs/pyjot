import os

import jot
import jot.log
from jot.influxdb import InfluxDB2Target


@jot.instrument
def send_metrics():
    jot.info("Starting InfluxDB2 example")
    jot.magnitude("cpu_usage", 75.7, service="web", host="server1")
    jot.count("requests", 100, service="web", host="server1")

    with jot.span("child1") as j:
        j.info("Child span processing")
        j.magnitude("memory_usage", 2048, host="server1")


def main():
    endpoint = os.getenv("INFLUXDB2_ENDPOINT", "http://localhost:8086")
    target = InfluxDB2Target(
        endpoint=endpoint,
        bucket="my-bucket",
        org="my-org",
        token="my-token",
        level=jot.log.ALL,
    )
    jot.init(target)
    send_metrics()


if __name__ == "__main__":
    main()
