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

    def all_for_branch_and_build(self, branch, build_id=None):
        """ Search for all results for the given branch and build number.
        If no build number is given, only the latest result is returned"""
        query = {}
        query["branch"] = branch
        if build_id:
            query["build_id"] = build_id

        res = self.col.find(query)
        if not build_id:
            res = res.sort([("created", pymongo.DESCENDING)]).limit(1)

        metrics = {}
        for data in res:
            metrics.update(data["metrics"])

        return metrics

    def bars(self, branch, build_id, reference):
        branch_metrics = self.all_for_branch_and_build(branch, build_id)
        reference_metrics = self.all_for_branch_and_build(reference)

        diff_against_self = False
        if reference_metrics == {}:
            print(f"** Reference branch {reference} does not have any metrics")
            print(f"** Comparing branch {branch} to self instead")
            reference_metrics = branch_metrics
            diff_against_self = True

        b, r = [], []
        ticks = []
        for field in branch_metrics.keys() | reference_metrics.keys():
            b.append(branch_metrics.get(field, {}).get("value", 0))
            r.append(reference_metrics.get(field, {}).get("value", 0))
            ticks.append(field)

        return b, r, ticks, diff_against_self

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
    BUILD_ID = env.build_id
    if env.is_pr:
        target_branch = env.target_branch
        branch, main, ticks, diff_against_self = m.bars(BRANCH, BUILD_ID, target_branch)

        values = m.normalise(branch, main)
        pos, neg = m.split(values)
        fig, ax = plt.subplots()
        index = np.arange(len(ticks))
        bar_width = 0.35
        opacity = 0.9
        ax.barh(index, pos, 0.3, alpha=opacity, color="blue", left=0)
        ax.barh(index, neg, 0.3, alpha=opacity, color="orange", left=0)
        ax.set_xlabel("Change")

        if not diff_against_self:
            print(f"Comparing {BRANCH} and {target_branch}")
            ax.set_title(f"{BRANCH} vs {target_branch}")
        else:
            ax.set_title(f"WARNING: {target_branch} does not have any data")

        ax.set_yticks(index)
        ax.set_yticklabels(ticks)
        ax.axvline(0, color="grey")
        plt.xlim([min(values + [0]) - 1, max(values) + 1])
        fmt = "%.0f%%"
        xticks = mtick.FormatStrFormatter(fmt)
        ax.xaxis.set_major_formatter(xticks)
        plt.tight_layout()
        plt.savefig(os.path.join(metrics_path, "diff.png"))

    else:
        print("Skipping since job is not a Pull Request")
