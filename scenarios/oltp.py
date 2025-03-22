#!/usr/bin/env python3
from time import sleep

import jot
from jot.otlp import OTLPTarget


def main():
    target = OTLPTarget.default(level=jot.log.ALL)
    jot.init(target, scenario="oltp-traces")

    jot.start("root")
    sleep(0.01)
    jot.info("hello", twif=76)
    jot.start("child1", zork=56)
    jot.info("hello", twif=6)
    jot.count("floops", 85)
    sleep(0.01)
    jot.finish()
    jot.start("child2", zork=21)
    sleep(0.02)
    jot.magnitude("magnitude", 1.0)
    jot.finish()
    jot.finish()


if __name__ == "__main__":
    main()
