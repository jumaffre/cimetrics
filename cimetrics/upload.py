# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import sys
import datetime
import yaml
import pymongo

from cimetrics.env import get_env


class Metrics(object):
    def __init__(self) -> None:
        self.env = get_env()
        self.metrics = {}

    def put(self, name: str, value: float) -> None:
        self.metrics[name] = {"value": value}

    def publish(self):
        try:
            self.env.mongo_connection
        except KeyError:
            print(
                "Results were not uploaded since METRICS_MONGO_CONNECTION env is not set."
            )
            return

        client = pymongo.MongoClient(self.env.mongo_connection)

        db = None
        coll = None
        try:
            db = client[self.env.mongo_db]
            coll = db[self.env.mongo_collection]
        except KeyError:
            print(
                'Results were not uploaded since "db" or "collection" have not been set.'
                f" Make sure you create the {self.env.config_file} file at the root of your repo."
            )
            return

        doc = {
            "created": datetime.datetime.now(),
            "build_id": self.env.build_id,
            "branch": self.env.branch,
            "is_pr": self.env.is_pr,
            "commit": self.env.commit,
            "metrics": self.metrics,
        }
        if self.env.is_pr:
            doc["target_branch"] = self.env.target_branch
        coll.insert_one(doc)
