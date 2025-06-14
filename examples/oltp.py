#!/usr/bin/env python3
from time import sleep

import jot
from jot.otlp import OTLPLogExporter, OTLPMetricExporter, OTLPSpanExporter, OTLPTarget
from jot.util import generate_span_id


def main():
    host = "alloy.yoshi-dev-alloy.svc.cluster.local"
    span_exporter = OTLPSpanExporter(f"http://{host}:4318/v1/traces")
    metric_exporter = OTLPMetricExporter(f"http://{host}:4318/v1/metrics")
    log_exporter = OTLPLogExporter(f"http://{host}:4318/v1/logs")
    target = OTLPTarget(
        span_exporter=span_exporter,
        metric_exporter=metric_exporter,
        log_exporter=log_exporter,
        level=jot.log.ALL,
    )

    extra_id = generate_span_id()
    jot.init(target, scenario="oltp-traces", extra_id=extra_id)

    with jot.span("root") as jr:
        sleep(0.01)
        jr.info("hello", twif=76)
        with jr.span("child1", zork=56) as j:
            j.info("hello", twif=6)
            j.count("floops", 85)
            sleep(0.01)
        with jot.span("child2", zork=21) as j:
            sleep(0.0)
            jot.magnitude("magnitude", 1.0)

        try:
            1 / 0
        except ZeroDivisionError as e:
            jr.error("division by zero", e, zork=21)


if __name__ == "__main__":
    main()
