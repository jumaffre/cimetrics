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
matplotlib.rcParams["axes.titlesize"] = 8


class Color:
    TARGET = "lightsteelblue"
    GOOD = "forestgreen"
    BAD = "firebrick"
    TICK = "silver"
    BACKGROUND = "white"


class Metrics(object):
    def __init__(self, env):
        if env is None:
            print("Environment is not Azure Pipelines or git repo. Skipping plotting.")
            return

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

    def branch_history(self, branch, max_build_id=None, max_builds=5):
        """
        Branch history as a dataframe, up to max_build_id, going back
        at most max_builds.
        """

        def flatten(entry):
            """
            Flatten an entry from the DB to a dict of metric: value,
            and numerical build_id
            """
            v = {k: v.get("value") for k, v in entry["metrics"].items()}
            v["build_id"] = int(entry["build_id"] or 0)
            return v

        # Discover build ids by descending order of created timestamp
        query = {"branch": branch}
        records = self.col.find(query, {"build_id": 1, "created": 1}).sort(
            [("created", pymongo.DESCENDING)]
        )

        # Collect at most max_builds, less or equal to max_build_id if specified
        build_ids = set()

        def less_than_max_build_id(record):
            return (max_build_id is None) or (
                int(record.get("build_id")) <= int(max_build_id)
            )

        for r in records:
            if r.get("build_id") and less_than_max_build_id(r):
                build_ids.add(r["build_id"])
                if len(build_ids) >= max_builds:
                    break

        # Get metrics for those build ids, ordered by build_ids
        query = {"branch": branch, "build_id": {"$in": list(build_ids)}}
        records = self.col.find(query, {"build_id": 1, "metrics": 1}).sort(
            [("build_id", pymongo.ASCENDING)]
        )

        # Index and collapse metrics by build_id
        df = (
            pandas.DataFrame.from_records([flatten(r) for r in records])
            .set_index("build_id")
            .groupby("build_id")
            .mean()
        )
        # Drop incomplete rows
        if "__complete" in df.columns:
            df = df.dropna(subset=["__complete"])
            df = df.drop(columns=["__complete"])
        # Drop columns for metrics that don't exist in the last build
        df = df[list(df.tail(1).dropna(axis="columns", how="all"))]
        return df


def trend_view(env):
    if env is None:
        print("Skipping plotting (env)")
        return

    try:
        m = Metrics(env)
    except ValueError as e:
        sys.exit(str(e))

    metrics_path = os.path.join(env.repo_root, "_cimetrics")
    os.makedirs(metrics_path, exist_ok=True)

    tgt_raw = m.branch_history(env.target_branch, max_builds=env.span * 2)
    tgt_ewma = tgt_raw.ewm(span=env.span).mean()
    tgt_cols = tgt_raw.columns
    tgt_raw = tgt_raw.tail(env.span)
    tgt_ewma = tgt_ewma.tail(env.span)

    branch_series = m.branch_history(env.branch, env.build_id)
    nrows = len(branch_series.columns)

    fig = plt.figure()
    first_ax = None
    ncol = env.columns
    for index, col in enumerate(sorted(branch_series.columns)):
        ax = fig.add_subplot(
            math.ceil(float(nrows) / ncol), ncol, index + 1, sharex=first_ax
        )
        ax.set_facecolor(Color.BACKGROUND)
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()

        if not first_ax:
            first_ax = ax
        if col in tgt_cols:
            # Plot raw target branch data
            ax.plot(
                tgt_raw[col].values,
                color=Color.TARGET,
                marker="o",
                markersize=1,
                linestyle="",
            )
            # Plot ewma of target branch data
            ax.plot(tgt_ewma[col].values, color=Color.TARGET, linewidth=0.5)

        # Pick color direction
        good_col, bad_col = Color.GOOD, Color.BAD
        if col.endswith("^"):
            good_col, bad_col = bad_col, good_col

        if col in branch_series.columns:
            branch_val = branch_series[col].values[-1]
            # Pick a marker, either caret up, down, or circle for new metrics
            if col in tgt_cols:
                lewm = tgt_ewma[col][tgt_ewma.index[-1]]
                marker, color = (7, good_col) if branch_val < lewm else (6, bad_col)
            else:
                lewm = branch_val
                marker, color = (".", Color.GOOD)

            # Plot marker for branch value
            marker_x = len(tgt_raw) + len(branch_series) - 1
            s = ax.plot(
                marker_x,
                [branch_val],
                color=color,
                marker=marker,
                markersize=6,
                linestyle="",
            )
            # Plot stem of arrow for branch value
            s = ax.plot(
                [marker_x, marker_x],
                [lewm, branch_val],
                color=color,
                linestyle="-",
                linewidth=1,
            )

            # Plot previous branch runs
            for bx, by in zip(range(len(tgt_raw), marker_x), branch_series[col]):
                s = ax.plot(
                    [bx, bx],
                    [lewm, by],
                    color=good_col if by < lewm else bad_col,
                    linestyle=":",
                    linewidth=1,
                )

            if col in tgt_ewma:
                # Annotate plot with % change
                percent_change = 100 * (branch_val - lewm) / lewm
                sign = "+" if percent_change > 0 else ""
                offset = 10
                plt.annotate(
                    f"{sign}{percent_change:.0f}%",
                    (len(tgt_raw) - 1, branch_val),
                    xytext=(offset + 10, offset if percent_change > 0 else -offset),
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
        ax.tick_params(axis="y", which="both", color=Color.TICK)
        ax.tick_params(axis="x", which="both", color=Color.TICK)
        # Match tick colors with series they belong to
        tls = ax.yaxis.get_ticklabels()
        tls[0].set_color(color)
        if len(tls) > 1:
            tls[1].set_color(Color.TARGET)
        # Don't print xticks for rows other than bottom
        if index + 1 < nrows - 1:
            plt.setp(ax.get_xticklabels(), visible=False)
            plt.setp(ax.get_xticklines(), visible=False)
            plt.setp(ax.spines.values(), visible=False)
        ax.set_xticks([0, len(tgt_raw) - 1])
        ax.set_xticklabels(
            [tgt_raw.index.values[0], tgt_raw.index.values[-1],], {"fontsize": 6},
        )

    plt.tight_layout()
    plt.savefig(os.path.join(metrics_path, "diff.png"), dpi=200)
    plt.close(fig)

    build_ids = sorted(tgt_raw.index)
    if build_ids:
        target_builds = f"{len(build_ids)} builds from [{build_ids[0]}]({env.build_url_by_id(build_ids[0])}) to [{build_ids[-1]}]({env.build_url_by_id(build_ids[-1])})"
        comment = f"{env.branch}@[{env.build_id} aka {env.build_number}]({env.build_url}) vs {env.target_branch} ewma over {target_builds}"
    else:
        comment = f"WARNING: {env.target_branch} does not have any data"
    print(comment)
    with open(os.path.join(metrics_path, "diff.txt"), "w") as dtext:
        dtext.write(comment)


if __name__ == "__main__":
    trend_view(get_env())
