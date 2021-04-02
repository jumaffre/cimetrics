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
from adtk.detector import LevelShiftAD

from cimetrics.env import get_env

plt.style.use("ggplot")


class Color:
    TARGET_RAW = "lightsteelblue"
    TARGET_TREND = "slategrey"
    GOOD = "forestgreen"
    BAD = "firebrick"
    TICK = "silver"
    BACKGROUND = "white"


class SmallFontSize:
    XTICKS = 4
    YTICKS = 4
    TITLE = 4
    DEFAULT = 4


class StandardFontSize:
    XTICKS = 4
    YTICKS = 4
    TITLE = 5
    DEFAULT = 4


def ticklabel_format(value):
    """
    Pick formatter for ytick labels. If possible, just print out the
    value with the same precision as the branch value. If that doesn't
    fit, switch to scientific format.
    """
    bvs = str(value)
    if len(bvs) < 7:
        fp = len(bvs) - (bvs.index(".") + 1) if "." in bvs else 0
        return f"%.{fp}f"
    else:
        return "%.1e"


def fancy_date(ds):
    return f"$_{{{ds[:4]}}}${ds[4:]}"


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

    def branch_history(self, branch_query, max_build_id=None, max_builds=5):
        """
        Branch history as a dataframe, up to max_build_id, going back
        at most max_builds.
        """

        id_to_number = {}

        def flatten(entry):
            """
            Flatten an entry from the DB to a dict of metric: value,
            and numerical build_id
            """
            v = {k: v.get("value") for k, v in entry["metrics"].items()}
            bid = int(entry["build_id"] or 0)
            v["build_id"] = bid
            id_to_number[bid] = entry.get("build_number", str(bid))
            return v

        # Discover build ids by descending order of created timestamp
        records = self.col.find(branch_query, {"build_id": 1, "created": 1}).sort(
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
        query = branch_query.copy()
        query["build_id"] = {"$in": list(build_ids)}
        records = self.col.find(
            query, {"build_id": 1, "metrics": 1, "build_number": 1}
        ).sort([("build_id", pymongo.ASCENDING)])

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
        return df, id_to_number


def anomalies(series, window_size):
    try:
        ts = series.set_index(pandas.date_range(start="1/1/1970", periods=len(series)))
        ad = LevelShiftAD(window=window_size, c=3)
        an = ad.fit_detect(ts).fillna(0).diff().fillna(0).reset_index(drop=True)
        return an[an > 0].dropna().index
    except RuntimeError as err:
        print(f"Could not detect anomalies: {err}")
        return []


def trend_view(env, tgt_only=False):
    if env is None:
        print("Skipping plotting (env)")
        return

    try:
        m = Metrics(env)
    except ValueError as e:
        sys.exit(str(e))

    metrics_path = os.path.join(env.repo_root, "_cimetrics")
    os.makedirs(metrics_path, exist_ok=True)

    span = env.monitoring_span if tgt_only else env.span
    # Try to have enough data for all ewma points to be
    # calculated from a full window
    build_span = span + env.ewma_span

    tgt_raw, tick_map = m.branch_history(
        {"branch": env.target_branch}, max_builds=build_span
    )
    tgt_ewma = tgt_raw.ewm(span=env.ewma_span).mean()
    tgt_cols = tgt_raw.columns
    tgt_raw = tgt_raw.tail(span)
    tgt_ewma = tgt_ewma.tail(span)
    first_ax = None

    if tgt_only:
        columns = sorted(tgt_raw.columns)
        ncol = env.monitoring_columns
        fsize = matplotlib.figure.figaspect(env.columns * 1.2)
        dpi_adjust = fsize[1] / matplotlib.rcParams["figure.figsize"][1]
        fig = plt.figure(figsize=fsize)
        font_size = SmallFontSize
    else:
        # On a PR, select older builds with the same PR id (assumed unique)
        # failing that, use the branch name, in which case we may pick up
        # uninteresting history if the branch name has been reused.
        if env.pull_request_id:
            query = {"pr_id": env.pull_request_id}
        else:
            query = {"branch": env.branch}
        branch_series, branch_tick_map = m.branch_history(query, env.build_id)
        tick_map.update(branch_tick_map)
        columns = sorted(branch_series.columns)
        ncol = env.columns
        fsize = matplotlib.figure.figaspect(1)
        dpi_adjust = fsize[1] / matplotlib.rcParams["figure.figsize"][1]
        fig = plt.figure(figsize=fsize)
        font_size = StandardFontSize

    # There is no easy way to set the size on annotate(), but we
    # otherwise explicitly set the size on each text element
    matplotlib.rcParams.update({"font.size": font_size.DEFAULT})
    nplot = len(columns)

    for index, col in enumerate(columns):
        nrow = math.ceil(float(nplot) / ncol)
        share = {}
        if not tgt_only:
            share["sharex"] = first_ax
        ax = fig.add_subplot(nrow, ncol, index + 1, **share)
        ax.set_facecolor(Color.BACKGROUND)
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()

        if not first_ax:
            first_ax = ax

        interesting_ticks = []

        if col in tgt_cols:
            # Plot raw target branch data
            ax.plot(
                tgt_raw[col].values,
                color=Color.TARGET_RAW,
                marker="o",
                markersize=0.5,
                linestyle="",
            )
            # Plot ewma of target branch data
            ax.plot(tgt_ewma[col].values, color=Color.TARGET_TREND, linewidth=0.5)

            _, ymax = plt.ylim()
            if tgt_only:
                for anomaly in anomalies(tgt_raw[col].to_frame(), env.ewma_span):
                    interesting_ticks.append(anomaly)
                    ax.axvline(x=anomaly, color=Color.BAD, linestyle=":", linewidth=0.5)
                    ev = tgt_ewma[col].iloc[anomaly]
                    ax.text(
                        anomaly,
                        ymax,
                        ticklabel_format(ev) % ev,
                        color=Color.BAD,
                        rotation=-30,
                        ha="right",
                    )

        if not tgt_only:
            # Pick color direction
            good_col, bad_col = Color.GOOD, Color.BAD
            if col.endswith("^"):
                good_col, bad_col = bad_col, good_col

            if col in branch_series.columns:
                branch_val = branch_series[col].values[-1]
                # Pick a marker, either caret up, down, or circle for new metrics
                if col in tgt_cols:
                    lewm = tgt_ewma[col][tgt_ewma.index[-1]]
                    marker, color = (1, good_col) if branch_val < lewm else (1, bad_col)
                else:
                    lewm = branch_val
                    marker, color = (1, Color.GOOD)

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
                        linestyle="-",
                        linewidth=1,
                        alpha=0.3,
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
        yt = []
        if tgt_only:
            yvals = tgt_raw[col].dropna().values
            yt.append(yvals.min())
            yt.append(yvals.max())
        else:
            yt.append(branch_val)
        if col in tgt_cols:
            yt.append(tgt_ewma[col].values[-1])
        ax.set_yticks(yt)
        ax.set_yticklabels(yt, {"fontsize": font_size.YTICKS})

        fmt = ticklabel_format(yt[0])
        ax.yaxis.set_major_formatter(mtick.FormatStrFormatter(fmt))
        padding = {}
        if tgt_only:
            padding["pad"] = 14
        ax.set_title(
            col.strip("^").strip(),
            loc="left",
            fontdict={"fontweight": "bold"},
            color="dimgray",
            fontsize=font_size.TITLE,
            **padding,
        )
        if tgt_only:
            ax.tick_params(
                axis="y",
                which="both",
                color=Color.TARGET_TREND,
                length=3,
                width=1,
                direction="in",
            )
        else:
            ax.tick_params(axis="y", right=False)
        ax.tick_params(
            axis="x",
            which="both",
            color=Color.TARGET_TREND,
            length=3,
            width=1,
            direction="in",
        )
        # Match tick colors with series they belong to
        tls = ax.yaxis.get_ticklabels()
        if not tgt_only:
            tls[0].set_color(color)
            if len(tls) > 1:
                tls[1].set_color(Color.TARGET_TREND)
        # Don't print xticks for rows other than bottom if not
        # in tgt_only mode
        if (index < (ncol * (nrow - 1))) and not tgt_only:
            plt.setp(ax.get_xticklabels(), visible=False)
            plt.setp(ax.get_xticklines(), visible=False)
            plt.setp(ax.spines.values(), visible=False)

        xticks = [0] + interesting_ticks + [len(tgt_raw) - 1]
        xticks_labels = [fancy_date(tick_map[tgt_raw.index.values[i]]) for i in xticks]

        if tgt_only:
            plt.xticks(rotation=-30, ha="left")
        else:
            plt.xticks(ha="left")
        ax.set_xticks(xticks)
        ax.set_xticklabels(
            xticks_labels,
            {"fontsize": font_size.XTICKS},
        )

    plt.tight_layout()
    plt.savefig(os.path.join(metrics_path, "diff.png"), dpi=200 * dpi_adjust)
    plt.close(fig)

    build_ids = sorted(tgt_raw.index)
    if build_ids:
        target_builds = f"{len(build_ids)} builds from [{build_ids[0]}]({env.build_url_by_id(build_ids[0])}) to [{build_ids[-1]}]({env.build_url_by_id(build_ids[-1])})"
        comment = f"{env.branch}@[{env.build_id} aka {env.build_number}]({env.build_url}) vs {env.target_branch} ewma over {target_builds}"
    else:
        comment = f"WARNING: {env.target_branch} does not have any data"
    print(comment)

    build_number = [tick_map[tgt_raw.index.values[i]] for i in range(len(tgt_raw))]
    tgt_raw.insert(loc=0, column="build_number", value=build_number)
    disable_numparse = [1]  # 0 is the index (build_id), 1 is build_number
    md = f"""
<details>
  <summary>Click to see table</summary>
  
  {tgt_raw.to_markdown(disable_numparse=disable_numparse)}
</details>
"""

    with open(os.path.join(metrics_path, "diff.txt"), "w") as dtext:
        dtext.write(comment)
        dtext.write(md)


if __name__ == "__main__":
    trend_view(get_env(), not get_env().is_pr)
