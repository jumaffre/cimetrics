# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import yaml
import pymongo
import os
import sys
import matplotlib.pyplot as plt
import numpy as np
import sys
import matplotlib.ticker as mtick

from cimetrics.env import get_env

plt.style.use("ggplot")


class Metrics(object):
    def __init__(self, env):
        self.client = pymongo.MongoClient(env.mongo_connection)
        db = self.client[env.mongo_db]
        self.col = db[env.mongo_collection]

    def all(self):
        return self.col.find()

    def last_for_branch(self, branch):
        return next(
            self.col.find({"branch": branch})
            .sort([("created", pymongo.DESCENDING)])
            .limit(1)
        )

    def bars(self, branch, reference):
        branch_metrics = self.last_for_branch(branch)["metrics"]
        reference_metrics = self.last_for_branch(reference)["metrics"]

        b, r = [], []
        ticks = []
        for field in branch_metrics.keys() | reference_metrics.keys():
            b.append(branch_metrics.get(field, {}).get("value", 0))
            r.append(reference_metrics.get(field, {}).get("value", 0))
            ticks.append(field)

        return b, r, ticks

    def normalise(self, new, ref):
        return [100 * (n - r) / r for n, r in zip(new, ref)]

    def split(self, series):
        pos, neg = [], []
        for v in series:
            if v > 0:
                pos.append(v)
                neg.append(0)
            else:
                pos.append(0)
                neg.append(v)
        return pos, neg


if __name__ == "__main__":
    env = get_env()
    metrics_path = os.path.join(env.repo_root, "_cimetrics")
    os.makedirs(metrics_path, exist_ok=True)
    m = Metrics(env)
    BRANCH = env.branch
    if env.is_pr:
        target_branch = env.target_branch
        print(f"Comparing {BRANCH} and {target_branch}")
        branch, main, ticks = m.bars(BRANCH, target_branch)
        values = m.normalise(branch, main)
        pos, neg = m.split(values)
        fig, ax = plt.subplots()
        index = np.arange(len(ticks))
        bar_width = 0.35
        opacity = 0.9
        ax.barh(index, pos, 0.3, alpha=opacity, color="blue", left=0)
        ax.barh(index, neg, 0.3, alpha=opacity, color="orange", left=0)
        ax.set_xlabel("Change")
        ax.set_title(f"{BRANCH} vs {target_branch}")
        ax.set_yticks(index)
        ax.set_yticklabels(ticks)
        ax.axvline(0, color="grey")
        plt.xlim([min(values + [0]) - 1, max(values) + 1])
        fmt = "%.0f%%"
        xticks = mtick.FormatStrFormatter(fmt)
        ax.xaxis.set_major_formatter(xticks)
        plt.tight_layout()
        plt.savefig(os.path.join(metrics_path, "diff.png"))
