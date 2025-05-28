#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import time

import jot
from jot.influxdb3 import InfluxDB3Target


def main():
    target = InfluxDB3Target(
        url="http://influx.yoshi-dev-influx.svc.cluster.local:8181/",
        token="apiv3_UyZCSoTuXYJTLIR_5uOkBsTPvxGv2xNRHII97RhdH_3ZmeJcdNHlb953Ia1GmbufmyZNFRzXeYcK8Tw4azuMRw",
        database="demo",
    )
    jot.init(target)

    print("Starting sine wave metric emission loop...")
    print("Press Ctrl+C to stop")

    start_time = time.time()
    counter = 0

    try:
        while True:
            current_time = time.time()
            elapsed = current_time - start_time

            # Generate sine wave values
            sine_value = math.sin(elapsed * 0.001) * 100  # Slow sine wave, amplitude 100
            fast_sine = math.sin(elapsed * 0.05) * 50  # Fast sine wave, amplitude 50
            cosine_value = math.cos(elapsed * 0.01) * 75  # Cosine wave, amplitude 75

            # Emit metrics
            jot.magnitude("sine_wave", sine_value, source="demo", wave_type="slow")
            jot.magnitude("sine_wave", fast_sine, source="demo", wave_type="fast")
            jot.magnitude("cosine_wave", cosine_value, source="demo")
            jot.count("sine_count", sine_value, source="demo")

            counter += 1

            # Print status every 10 iterations
            if counter % 10 == 0:
                print(
                    f"Iteration {counter}: sine={sine_value:.2f}, fast_sine={fast_sine:.2f}, cosine={cosine_value:.2f}"
                )

            # Sleep for 1 second
            time.sleep(0.1)

    except KeyboardInterrupt:
        print(f"\nStopped after {counter} iterations")


if __name__ == "__main__":
    main()
