# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import sys
import random

import cimetrics.upload

metrics = cimetrics.upload.Metrics()

metrics.put('Signed throughput', random.randint(50_000, 100_0000))
metrics.put('Unsigned throughput', random.randint(50_000, 100_000))
metrics.put('Local latency', random.randint(10, 100))
metrics.put('Global latency', random.randint(10, 100))
metrics.put('Geo-replicated latency', random.randint(10, 100))

metrics.publish()
