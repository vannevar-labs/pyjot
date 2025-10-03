#!/usr/bin/env python3
from time import sleep

import jot


def main():
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
