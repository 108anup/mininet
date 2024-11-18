from math import log
import os
from typing import Dict, Tuple
from matplotlib import pyplot as plt
import matplotlib as mpl
import pandas as pd
import scipy

import imc_dumbbell
import imc_parking_lot
import imc_jitter


from plot_config.figure_type_creator import FigureTypeCreator
ftc = FigureTypeCreator(pub_type='paper', paper_use_small_font=True)
paper = ftc.get_figure_type()


from plot_config_light import get_fig_size_paper, get_style, colors, markers

my_style = get_style(True, True, True)

RENAME = {
    "sqrt": "$1/\sqrt{s}$",
    "vegas": "$1/s$",
    "swift": "$1/s^2$",
}
SORT_ORDER = [
    "sqrt",
    "vegas",
    "swift",
]
SORT_ORDER_MAP = {k: i for i, k in enumerate(SORT_ORDER)}
INVERSE_SORT_ORDER_MAP = {i: k for i, k in enumerate(SORT_ORDER)}


@mpl.rc_context(my_style)
def plot_fit(
    df: pd.DataFrame,
    xl: str,
    yl: str,
    func_dict: Dict,
    outpath: str,
    xlabel: str,
    ylabel: str,
    title: str = None,
    ylim: Tuple = (None, None),
    loglog: bool = False,
):
    figsize = get_fig_size_paper(xscale=0.3, yscale=0.3, full=True)
    fig, ax = plt.subplots(figsize=figsize)
    # fig, ax = paper.subfigures(xscale=0.5, yscale=0.5)
    i = 0
    df["scheme_id"] = df["scheme"].map(SORT_ORDER_MAP)
    df = df.sort_values(["scheme", xl])
    for scheme_id, gdf in df.groupby('scheme_id'):
        if xl == "jitter_us" and loglog:
            gdf = gdf.iloc[1:]

        assert isinstance(scheme_id, int)
        scheme = INVERSE_SORT_ORDER_MAP[scheme_id]
        func = func_dict[scheme]
        ret = scipy.optimize.curve_fit(func, gdf[xl], gdf[yl])
        print(scheme, ret)

        ax.plot(
            gdf[xl],
            func(gdf[xl], *ret[0]),
            marker='',
            ls="--",
            color="grey",
            label=f"_",
        )
        ax.plot(
            gdf[xl],
            gdf[yl],
            ls="None",
            marker=markers[i],
            color=colors[i],
            label=RENAME[scheme],
        )
        i += 1

    ax.set_title(title)
    ax.legend()
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if loglog:
        ax.set_xscale('log')
        ax.set_yscale('log')
    else:
        ax.set_ylim(ylim)
    fig.tight_layout(pad=0.03)
    fig.savefig(outpath, pad_inches=0.03)


if __name__ == "__main__":
    BASE_INPUT_PATH = "/home/anupa/Projects/msr24/uec-experiments/imc/contracts/"
    BASE_OUTPUT_PATH = '/home/anupa/Projects/Verification/CCmatic-empirical/experiments/figs/mininet'

    fpath = os.path.join(BASE_INPUT_PATH, "multiflow/max-cwnd/ssqueue-vs-nflows.csv")
    df = pd.read_csv(fpath)
    opath = os.path.join(BASE_OUTPUT_PATH, 'fit_dumbbell.pdf')
    opath_loglog = os.path.join(BASE_OUTPUT_PATH, 'fit_dumbbell_loglog.pdf')
    plot_fit(
        df,
        "num_flows",
        "avg_queue_bdp",
        imc_dumbbell.FUNC_DICT,
        opath,
        "Number of Flows",
        "Queue Size [BDP]",
        title="Congestion growth (lower better)",
        ylim=(None, 10),
    )
    plot_fit(
        df,
        "num_flows",
        "avg_queue_bdp",
        imc_dumbbell.FUNC_DICT,
        opath_loglog,
        "Number of Flows",
        "Queue Size [BDP]",
        title="Congestion growth (lower better)",
        loglog=True,
    )

    fpath = os.path.join(BASE_INPUT_PATH, "parking_lot/max-cwnd/xratio-vs-hopcount.csv")
    df = pd.read_csv(fpath)
    opath = os.path.join(BASE_OUTPUT_PATH, 'fit_parkinglot.pdf')
    opath_loglog = os.path.join(BASE_OUTPUT_PATH, 'fit_parkinglot_loglog.pdf')
    plot_fit(
        df,
        "hop_count",
        "throughput_ratio",
        imc_parking_lot.FUNC_DICT,
        opath,
        "Hop count",
        "Throughput ratio",
        title="Unfairness (lower better)",
        ylim=(None, 80),
    )
    plot_fit(
        df,
        "hop_count",
        "throughput_ratio",
        imc_parking_lot.FUNC_DICT,
        opath_loglog,
        "Hop count",
        "Throughput ratio",
        title="Unfairness (lower better)",
        loglog=True
    )

    fpath = os.path.join(BASE_INPUT_PATH, "jitter/first/xratio-vs-jitter.csv")
    df = pd.read_csv(fpath)
    opath = os.path.join(BASE_OUTPUT_PATH, 'fit_jitter.pdf')
    opath_loglog = os.path.join(BASE_OUTPUT_PATH, 'fit_jitter_loglog.pdf')
    plot_fit(
        df,
        "jitter_us",
        "throughput_ratio",
        imc_jitter.FUNC_DICT,
        opath,
        "Jitter [$\sim S_{min}$]",
        "Throughput ratio",
        title="Robustness error (lower better)",
        ylim=(None, 30),
    )
    plot_fit(
        df,
        "jitter_us",
        "throughput_ratio",
        imc_jitter.FUNC_DICT,
        opath_loglog,
        "Jitter [$\sim S_{min}$]",
        "Throughput ratio",
        title="Robustness error (lower better)",
        loglog=True,
    )
