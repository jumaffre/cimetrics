import os
import sys
import random

ROOT_DIR = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(ROOT_DIR)
import pymetrics

metrics = pymetrics.Metrics()

metrics.put('throughput', random.random())
metrics.put('latency', random.randint(10, 100))

metrics.publish()
