from math import log
import os
from typing import Dict, Tuple
from matplotlib import pyplot as plt
import pandas as pd
import scipy

import imc_dumbbell
import imc_parking_lot
import imc_jitter


def plot_fit(
    df: pd.DataFrame,
    xl: str,
    yl: str,
    func_dict: Dict,
    outpath: str,
    xlabel: str,
    ylabel: str,
    ylim: Tuple = (None, None),
    loglog: bool = False,
):
    fig, ax = plt.subplots()
    for scheme, gdf in df.groupby('scheme'):
        assert isinstance(scheme, str)
        func = func_dict[scheme]
        ret = scipy.optimize.curve_fit(func, gdf[xl], gdf[yl])
        print(scheme, ret)

        ax.plot(gdf[xl], gdf[yl], 'X', label=f'{scheme}_data')
        ax.plot(gdf[xl], func(gdf[xl], *ret[0]), label=f'{scheme}_contract')

    ax.legend()
    ax.grid()
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if loglog:
        ax.set_xscale('log')
        ax.set_yscale('log')
    else:
        ax.set_ylim(ylim)
    fig.tight_layout()
    fig.savefig(outpath)


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
        (None, 10),
    )
    plot_fit(
        df,
        "num_flows",
        "avg_queue_bdp",
        imc_dumbbell.FUNC_DICT,
        opath_loglog,
        "Number of Flows",
        "Queue Size [BDP]",
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
        (None, 70),
    )
    plot_fit(
        df,
        "hop_count",
        "throughput_ratio",
        imc_parking_lot.FUNC_DICT,
        opath_loglog,
        "Hop count",
        "Throughput ratio",
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
        "Jitter (~ unit of Smin)",
        "Throughput ratio",
        (None, 30),
    )
    plot_fit(
        df,
        "jitter_us",
        "throughput_ratio",
        imc_jitter.FUNC_DICT,
        opath_loglog,
        "Jitter (~ unit of Smin)",
        "Throughput ratio",
        loglog=True,
    )
