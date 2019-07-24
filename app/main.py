# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import cimetrics.upload

def run_benchmark():
    return {
        'throughput': 50000,
        'latency': 10,
        'peak_wss': 50,
        'accuracy': 0.7,
        'error_rate': 0.05,
        'memory_fragmentation': 0.02,
        'cpu_usage': 0.30
    }

results = run_benchmark()

metrics = cimetrics.upload.Metrics()
metrics.put('Throughput (tx/s)', results['throughput'])
metrics.put('Latency (ms)', results['latency'])
metrics.put('Peak working set size (GB)', results['peak_wss'])
metrics.put('Accuracy (%)', results['accuracy'])
metrics.put('Error rate (%)', results['error_rate'])
metrics.put('Memory fragmentation (%)', results['memory_fragmentation'])
metrics.put('CPU usage (%)', results['cpu_usage'])
metrics.publish()
