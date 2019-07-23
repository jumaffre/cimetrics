import os
import sys
import random

import pymetrics.upload

metrics = pymetrics.upload.Metrics()

metrics.put('signed_throughput', random.randint(50_000, 100_0000))
metrics.put('unsigned_throughput', random.randint(50_000, 100_000))
metrics.put('local_latency', random.randint(10, 100))
metrics.put('global_latency', random.randint(10, 100))
metrics.put('geo_replicated_latency', random.randint(10, 100))

metrics.publish()
