# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import cimetrics.upload

def run_benchmark():
    return {
        'throughput': 50100,
        'latency': 15,
        'peak_wss': 55
    }

results = run_benchmark()

metrics = cimetrics.upload.Metrics()
metrics.put('Throughput', results['throughput'])
metrics.put('Latency', results['latency'])
metrics.put('Peak working set size', results['peak_wss'])
metrics.publish()
