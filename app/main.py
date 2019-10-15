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
    }


results = run_benchmark()

metrics = cimetrics.upload.Metrics()
metrics.put("Throughput (tx/s)", results["throughput"])
metrics.put("Latency (ms)", results["latency"])
metrics.put("Peak working set size (GB)", results["peak_wss"])
metrics.put("Accuracy (%)", results["accuracy"])
metrics.put("Error rate (%)", results["error_rate"])
metrics.put("Memory fragmentation (%)", results["memory_fragmentation"])
metrics.put("CPU usage (%)", results["cpu_usage"])
metrics.put("New metric (U)", results["new_metric"])
metrics.publish()
