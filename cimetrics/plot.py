# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import yaml
import pymongo
import pandas
import os
import sys
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import sys
import math
import matplotlib.ticker as mtick

from cimetrics.env import get_env

plt.style.use("ggplot")
matplotlib.rcParams["text.hinting"] = 1
matplotlib.rcParams["font.size"] = 6

TARGET_COLOR = "lightsteelblue"
BRANCH_GOOD_COLOR = "forestgreen"
BRANCH_BAD_COLOR = "firebrick"
TICK_COLOR = "silver"


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

    def ewma_all_for_branch_series(self, branch, span=10):
        """
        Return exponentially moving averages for all current metrics on
        the specified branch.
        """
        # Slightly unhappy wrapping/unwrapping calls, we should probably
        # simplify the data format to make it more pandable
        def values_from(d):
            return {k: v.get("value") for k, v in d.items()}

        def mrow(d):
            v = values_from(d["metrics"])
            v["build_id"] = int(d["build_id"] or 0)
            return v

        # Find the span * 2 most recent build ids
        query = {"branch": branch}
        res = self.col.find(query, {"build_id": 1, "created": 1}).sort(
            [("created", pymongo.DESCENDING)]
        )
        build_ids = set()
        for r in res:
            if r.get("build_id"):
                build_ids.add(r["build_id"])
                if len(build_ids) >= span * 2:
                    break

        # Get metrics for those build ids
        query = {"branch": branch, "build_id": {"$in": list(build_ids)}}
        res = self.col.find(query, {"build_id": 1, "metrics": 1}).sort(
            [("build_id", pymongo.ASCENDING)]
        )

        bids = sorted(build_ids)

        # Index and collapse metrics by build_id
        df = (
            pandas.DataFrame.from_records([mrow(r) for r in res])
            .set_index("build_id")
            .groupby("build_id")
            .mean()
        )
        # Drop columns for metrics that don't exist in the last build
        df = df[list(df.tail(1).dropna(axis="columns", how="all"))]
        # Run EWM over metrics
        ewr = df.ewm(span=span).mean()
        return df, ewr, bids

    def ewma_all_for_branch(self, branch, span=5):
        def values(d):
            return {k: {"value": v} for k, v in d.items()}

        _, df, bids = self.ewma_all_for_branch_series(branch, span)
        ewr = df.tail(1).to_dict("index")

        metrics = {}
        for data in ewr.values():
            metrics.update(data)

        return values(metrics), bids

    def bars(self, branch, build_id, reference):
        branch_metrics = self.all_for_branch_and_build(branch, build_id)
        reference_metrics, bids = self.ewma_all_for_branch(reference)

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
            # it's either delete, in which case we drop it, or new
            if b_v is None:
                continue
            elif r_v is None:
                r_v = b_v
                prefix = "[NEW]"

            b.append(b_v)
            r.append(r_v)
            ticks.append(f"{prefix} {field}")

        return b, r, ticks, diff_against_self, bids

    def normalise(self, new, ref):
        return [100 * (n - r) / r for n, r in zip(new, ref)]

    def split(self, series):
        pos, neg = [], []
        for v in series:
            if v >= 0:
                pos.append(v)
                neg.append(0)
            else:
                pos.append(0)
                neg.append(v)
        return pos, neg


def trend_view(env):
    metrics_path = os.path.join(env.repo_root, "_cimetrics")
    os.makedirs(metrics_path, exist_ok=True)
    try:
        m = Metrics(env)
    except ValueError as e:
        sys.exit(str(e))

    # TODO: merge dfs, get rid of build_ids
    tgt_raw, tgt_ewma, build_ids = m.ewma_all_for_branch_series(
        env.target_branch, env.span
    )
    tgt_cols = tgt_raw.columns
    branch = m.all_for_branch_and_build(env.branch, env.build_id)
    nrows = len(branch.keys())

    # TODO: get rid of rcParam if possible?
    plt.rcParams["axes.titlesize"] = 8
    fig = plt.figure()
    first_ax = None
    ncol = env.columns
    for index, col in enumerate(sorted(branch.keys())):
        ax = fig.add_subplot(
            math.ceil(float(nrows) / ncol), ncol, index + 1, sharex=first_ax
        )
        ax.set_facecolor("white")
        ax.grid(color="gainsboro", axis="x")

        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()

        if not first_ax:
            first_ax = ax
        if col in tgt_cols:
            # Plot raw target branch data as markers
            ax.plot(
                tgt_raw[col].values,
                color=TARGET_COLOR,
                marker="o",
                markersize=1,
                linestyle="",
            )
            # Plot ewma of target branch data
            ax.plot(tgt_ewma[col].values, color=TARGET_COLOR, linewidth=0.5)
        # Pick color direction for change arrow
        good_col, bad_col = (BRANCH_GOOD_COLOR, BRANCH_BAD_COLOR)
        if col.endswith("^"):
            good_col, bad_col = (bad_col, good_col)

        if col in branch:
            branch_val = branch[col]["value"]
            # Pick a marker, either caret up, down, or circle for new metrics
            if col in tgt_cols:
                lewm = tgt_ewma[col][tgt_ewma.index[-1]]
                marker, color = (7, good_col) if branch_val < lewm else (6, bad_col)
            else:
                lewm = branch_val
                marker, color = (".", BRANCH_GOOD_COLOR)
            # Plot marker for branch value
            s = ax.plot(
                [len(tgt_raw) - 1],
                [branch_val],
                color=color,
                marker=marker,
                markersize=6,
                linestyle="",
            )
            # Plot stem of arrow for branch value
            s = ax.plot(
                [len(tgt_raw) - 1] * 2,
                [lewm, [branch[col]["value"]][0]],
                color=color,
                linestyle="-",
                linewidth=1,
            )

            if col in tgt_ewma:
                # Annotate plot with % change
                percent_change = m.normalise([branch_val], [lewm])[0]
                sign = "+" if percent_change > 0 else ""
                offset = 10
                plt.annotate(
                    f"{sign}{percent_change:.0f}%",
                    (len(tgt_raw) - 1, branch_val),
                    xytext=(offset, offset if percent_change > 0 else -offset),
                    textcoords="offset points",
                    va="center",
                    ha="left",
                    color=color,
                    weight="bold",
                )
        # Set yticks to branch value and last ewma when applicable
        yt = [branch_val]
        if col in tgt_cols:
            yt.append(tgt_ewma[col].values[-1])
        ax.set_yticks(yt)
        ax.set_yticklabels(yt, {"fontsize": 6})
        # Pick formatter for ytick labels. If possible, just print out the
        # value with the same precision as the branch value. If that doesn't
        # fit, switch to scientific format.
        bvs = str(yt[0])
        if len(bvs) < 7:
            fp = len(bvs) - (bvs.index(".") + 1) if "." in bvs else 0
            fmt = f"%.{fp}f"
            ax.yaxis.set_major_formatter(mtick.FormatStrFormatter(fmt))
        else:
            fmt = "%.1e"
            ax.yaxis.set_major_formatter(mtick.FormatStrFormatter(fmt))
        ax.set_title(
            col.strip("^").strip(),
            loc="left",
            fontdict={"fontweight": "bold"},
            color="dimgray",
        )
        ax.tick_params(axis="y", which="both", color=TICK_COLOR)
        ax.tick_params(axis="x", which="both", color=TICK_COLOR)
        # Match tick colors with series they belong to
        tls = ax.yaxis.get_ticklabels()
        tls[0].set_color(color)
        if len(tls) > 1:
            tls[1].set_color(TARGET_COLOR)
        # Don't print xticks for rows other than bottom
        if index + 1 < nrows - 1:
            plt.setp(ax.get_xticklabels(), visible=False)
            plt.setp(ax.get_xticklines(), visible=False)
            plt.setp(ax.spines.values(), visible=False)
        ax.set_xticks([0, len(tgt_raw) - env.span, len(tgt_raw) - 1])
        ax.set_xticklabels(
            [
                tgt_raw.index.values[0],
                tgt_raw.index.values[-env.span],
                tgt_raw.index.values[-1],
            ],
            {"fontsize": 6},
        )

    plt.tight_layout()
    plt.savefig(os.path.join(metrics_path, "diff.png"), dpi=200)
    plt.close(fig)

    if build_ids:
        target_builds = f"{len(build_ids)} builds from [{build_ids[0]}]({env.build_url_by_id(build_ids[0])}) to [{build_ids[-1]}]({env.build_url_by_id(build_ids[-1])})"
        comment = f"{env.branch}@[{env.build_id} aka {env.build_number}]({env.build_url}) vs {env.target_branch} ewma over {target_builds}"
    else:
        comment = f"WARNING: {env.target_branch} does not have any data"
    print(comment)
    with open(os.path.join(metrics_path, "diff.txt"), "w") as dtext:
        dtext.write(comment)


def default_view(env):
    metrics_path = os.path.join(env.repo_root, "_cimetrics")
    os.makedirs(metrics_path, exist_ok=True)
    try:
        m = Metrics(env)
    except ValueError as e:
        sys.exit(str(e))

    BRANCH = env.branch
    BUILD_ID = env.build_id
    target_branch = env.target_branch
    branch, main, ticks, diff_against_self, bids = m.bars(
        BRANCH, BUILD_ID, target_branch
    )

    values = m.normalise(branch, main)
    pos, neg = m.split(values)
    fig, ax = plt.subplots(constrained_layout=True)
    ax.set_facecolor("white")
    ax.grid(color="whitesmoke", axis="x")
    index = np.arange(len(ticks))
    bar_width = 0.35
    opacity = 0.9
    pbars = ax.barh(index, pos, 0.3, alpha=opacity, color="darkkhaki", left=0)
    nbars = ax.barh(index, neg, 0.3, alpha=opacity, color="sandybrown", left=0)

    for i, (pbar, nbar) in enumerate(zip(pbars, nbars)):
        if pbar.get_width() >= 0 and nbar.get_width() == 0:
            x = pbar.get_width()
            y = pbar.get_y() + pbar.get_height() / 2
            plt.annotate(
                str(branch[i]),
                (x, y),
                xytext=(3, 0),
                textcoords="offset points",
                va="center",
                ha="left",
            )
        else:
            x = nbar.get_width()
            y = nbar.get_y() + nbar.get_height() / 2
            plt.annotate(
                str(branch[i]),
                (x, y),
                xytext=(-3, 0),
                textcoords="offset points",
                va="center",
                ha="right",
            )

    comment = ""
    if not diff_against_self:
        builds_ids = list(bids)
        target_builds = f"{len(bids)} builds from [{bids[0]}]({env.build_url_by_id(bids[0])}) to [{bids[-1]}]({env.build_url_by_id(bids[-1])})"
        comment = f"{BRANCH}@[{env.build_id} aka {env.build_number}]({env.build_url}) vs {target_branch} ewma over {target_builds}"
    else:
        comment = f"WARNING: {target_branch} does not have any data"
    print(comment)
    with open(os.path.join(metrics_path, "diff.txt"), "w") as dtext:
        dtext.write(comment)

    ax.set_yticks(index)
    ax.yaxis.set_ticks_position("none")
    ax.set_yticklabels(ticks)
    ax.axvline(0, color="grey")
    plt.xlim([min(values + [0]) - 5, max(values) + 5])
    fmt = "%.0f%%"
    xticks = mtick.FormatStrFormatter(fmt)
    ax.xaxis.set_major_formatter(xticks)
    plt.savefig(os.path.join(metrics_path, "diff.png"))


def render_and_save():
    env = get_env()
    (trend_view if env.view == "trend" else default_view)(env)


if __name__ == "__main__":
    render_and_save()
