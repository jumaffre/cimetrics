import os
import sys
import random

import pymetrics.upload

metrics = pymetrics.upload.Metrics()

metrics.put('Signed throughput', random.randint(50_000, 100_0000))
metrics.put('Unsigned throughput', random.randint(50_000, 100_000))
metrics.put('Local latency', random.randint(10, 100))
metrics.put('Global latency', random.randint(10, 100))
metrics.put('Geo-replicated latency', random.randint(10, 100))

metrics.publish()
