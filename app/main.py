# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import cimetrics.upload
import random


def run_benchmark():
    return {
        "throughput": random.randint(46000, 52000),
        "latency": random.randint(9, 11),
        "peak_wss": random.randint(45, 55),
        "accuracy": random.randint(68, 73) / 100,
        "error_rate": random.randint(4, 6) / 100,
        "memory_fragmentation": random.randint(18, 22) / 1000,
        "cpu_usage": random.randint(28, 32) / 100,
        "new_metric": random.randint(100, 200),
        "another_new_metric": random.randint(100, 200),
    }


results = run_benchmark()

with cimetrics.upload.metrics() as m:
    m.put("Throughput (tx/s)", results["throughput"])
    m.put("Latency (ms)", results["latency"])
    m.put("Peak working set size (GB)", results["peak_wss"])
    m.put("Accuracy (%)", results["accuracy"])
    m.put("Error rate (%)", results["error_rate"])
    m.put("Memory fragmentation (%)", results["memory_fragmentation"])
    m.put("CPU usage (%)", results["cpu_usage"])
    m.put("New metric (U)", results["new_metric"])