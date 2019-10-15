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
        try:
            env.mongo_connection
        except KeyError:
            raise ValueError(
                "Results were not uploaded since METRICS_MONGO_CONNECTION env is not set."
            )
            return

        self.client = pymongo.MongoClient(env.mongo_connection)

        db = None
        self.col = None
        try:
            db = self.client[env.mongo_db]
            self.col = db[env.mongo_collection]
        except KeyError:
            raise ValueError(
                'Results were not uploaded since "db" or "collection" have not been set.'
                f" Make sure you create the {env.config_file} file at the root of your repo."
            )

    def all_for_branch_and_build(self, branch, build_id=None):
        """ Search for all results for the given branch and build number.
        If no build number is given, only the latest result is returned"""
        query = {}
        query["branch"] = branch
        if build_id:
            query["build_id"] = build_id

        res = self.col.find(query)
        if not build_id:
            # If there is no build_id, retrieve the latest result
            res = res.sort([("created", pymongo.DESCENDING)]).limit(1)
            for data in res:
                build_id = data["build_id"]
            query["build_id"] = build_id
            res = self.col.find(query)

        metrics = {}
        for data in res:
            metrics.update(data["metrics"])

        return metrics

    def bars(self, branch, build_id, reference):
        branch_metrics = self.all_for_branch_and_build(branch, build_id)
        reference_metrics = self.all_for_branch_and_build(reference)

        if branch_metrics == {}:
            raise ValueError(
                f"Branch {branch} does not have any metrics for build {build_id}"
            )

        diff_against_self = False
        if reference_metrics == {}:
            print(
                f"Reference branch {reference} does not have any metrics."
                f" Comparing branch {branch} to self instead."
            )
            reference_metrics = branch_metrics
            diff_against_self = True

        b, r = [], []
        ticks = []

        for field in sorted(
            branch_metrics.keys() | reference_metrics.keys(), reverse=True
        ):
            prefix = ""
            b_v = branch_metrics.get(field, {}).get("value")
            r_v = reference_metrics.get(field, {}).get("value")

            # If there is no value for a given metric on the branch or reference,
            # give it the value of the other and mark as deleted/new.
            if b_v is None:
                b_v = r_v
                prefix = "[DELETED]"
            elif r_v is None:
                r_v = b_v
                prefix = "[NEW]"

            b.append(b_v)
            r.append(r_v)
            ticks.append(f"{prefix} {field}")

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
    try:
        m = Metrics(env)
    except ValueError as e:
        sys.exit(str(e))

    BRANCH = env.branch
    BUILD_ID = env.build_id
    target_branch = env.target_branch
    branch, main, ticks, diff_against_self = m.bars(BRANCH, BUILD_ID, target_branch)

    values = m.normalise(branch, main)
    pos, neg = m.split(values)
    fig, ax = plt.subplots(constrained_layout=True)
    ax.set_facecolor("white")
    ax.grid(color="whitesmoke", axis="x")
    index = np.arange(len(ticks))
    bar_width = 0.35
    opacity = 0.9
    bars = ax.barh(index, pos, 0.3, alpha=opacity, color="darkkhaki", left=0)

    for i, bar in enumerate(bars):
        x = bar.get_width()
        y = bar.get_y() + bar.get_height() / 2
        if x:
            plt.annotate(
                str(branch[i]),
                (x, y),
                xytext=(3, 0),
                textcoords="offset points",
                va="center",
                ha="left",
            )

    bars = ax.barh(index, neg, 0.3, alpha=opacity, color="sandybrown", left=0)

    for i, bar in enumerate(bars):
        x = bar.get_width()
        y = bar.get_y() + bar.get_height() / 2
        if x:
            plt.annotate(
                str(branch[i]),
                (x, y),
                xytext=(-3, 0),
                textcoords="offset points",
                va="center",
                ha="right",
            )

    if not diff_against_self:
        print(f"Comparing {BRANCH} and {target_branch}")
        ax.set_title(f"{BRANCH} vs {target_branch}")
    else:
        ax.set_title(f"WARNING: {target_branch} does not have any data")

    ax.set_yticks(index)
    ax.yaxis.set_ticks_position("none")
    ax.set_yticklabels(ticks)
    ax.axvline(0, color="grey")
    plt.xlim([min(values + [0]) - 3, max(values) + 3])
    fmt = "%.0f%%"
    xticks = mtick.FormatStrFormatter(fmt)
    ax.xaxis.set_major_formatter(xticks)
    plt.savefig(os.path.join(metrics_path, "diff.png"))
