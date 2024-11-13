import scipy.optimize
import numpy as np
import pandas as pd
import os
from matplotlib import pyplot as plt


STORAGE_ROOT = '/home/anupa/Projects/Verification/CCmatic-empirical/experiments/figs/mininet'


def func_sqrt(x, a):
    return a * np.sqrt(x)


def func_swift(x, a):
    return a * np.power(x, 2)


def func_vegas(x, a):
    return a * x


FUNC_DICT = {
    'swift': func_swift,
    'vegas': func_vegas,
    'sqrt': func_sqrt,
}

if __name__ == '__main__':
    fpath = "/home/anupa/Projects/msr24/uec-experiments/imc/contracts/parking_lot/max-cwnd/xratio-vs-hopcount.csv"
    df = pd.read_csv(fpath)
    #   scheme  hop_count  throughput_ratio
    xl = 'hop_count'
    yl = 'throughput_ratio'

    fig, ax = plt.subplots()
    for scheme, gdf in df.groupby('scheme'):
        assert isinstance(scheme, str)
        func = FUNC_DICT[scheme]
        ret = scipy.optimize.curve_fit(func, gdf[xl], gdf[yl])
        print(scheme, ret)

        ax.plot(gdf[xl], gdf[yl], 'X', label=f'{scheme}_data')
        ax.plot(gdf[xl], func(gdf[xl], *ret[0]), label=f'{scheme}_contract')
        ax.legend()
        ax.grid()
        ax.set_xlabel('Hop count')
        ax.set_ylabel('Throughput ratio')
        ax.set_ylim(None, 60)
        # ax.set_xscale('log')
        # ax.set_yscale('log')
        fig.tight_layout()
        fig.savefig(os.path.join(STORAGE_ROOT, 'fit_parking_lot.png'))
