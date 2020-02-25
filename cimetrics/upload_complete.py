# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import cimetrics.upload

if __name__ == "__main__":
    with cimetrics.upload.metrics() as m:
        pass
