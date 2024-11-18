import scipy.optimize
import numpy as np
import pandas as pd
import os
from matplotlib import pyplot as plt


STORAGE_ROOT = '/home/anupa/Projects/Verification/CCmatic-empirical/experiments/figs/mininet'


def func_sqrt(x, a, b):
    return np.sqrt(a * x + b)


def func_swift(x, a, b):
    return np.power(a * x + b, 2)


def func_vegas(x, a, b):
    return a * x + b


FUNC_DICT = {
    'swift': func_swift,
    'vegas': func_vegas,
    'sqrt': func_sqrt,
}

if __name__ == '__main__':
    fpath = "/home/anupa/Projects/msr24/uec-experiments/imc/contracts/jitter/first/xratio-vs-jitter.csv"
    df = pd.read_csv(fpath)
    #   scheme  jitter_us  throughput_ratio

    xl = 'jitter_us'
    yl = 'throughput_ratio'

    fig, ax = plt.subplots()
    for scheme, _gdf in df.groupby('scheme'):
        gdf = _gdf.sort_values(xl).iloc[1:]
        # gdf = _gdf
        assert isinstance(scheme, str)
        func = FUNC_DICT[scheme]
        ret = scipy.optimize.curve_fit(func, gdf[xl], gdf[yl])
        print(scheme, ret)

        ax.plot(gdf[xl], gdf[yl], 'X', label=f'{scheme}_data')
        ax.plot(gdf[xl], func(gdf[xl], *ret[0]), label=f'{scheme}_contract')
    ax.legend()
    ax.grid()
    ax.set_xlabel('Jitter (roughly in units of Smin)')
    ax.set_ylabel('Throughput ratio')
    ax.set_ylim(None, 30)
    # ax.set_xscale('log')
    # ax.set_yscale('log')
    fig.tight_layout()
    fig.savefig(os.path.join(STORAGE_ROOT, 'fit_jitter.png'))

