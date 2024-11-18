# Convert below to csv format:
import math
import os
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import scipy


STORAGE_ROOT = '/home/anupa/Projects/Verification/CCmatic-empirical/experiments/figs/mininet'

outputs = ["""
simplified_swift          2     23052.148438
simplified_swift          3     31665.156250
simplified_swift          4     39794.218750
simplified_swift          5     46762.421875
simplified_swift          6     49713.151042
simplified_swift          7     54294.877232
simplified_swift          8     58693.730469
simplified_swift          9     63950.069444
simplified_swift         10     67895.343750
simplified_swift         11     72168.650568
simplified_swift         12     76950.520833
simplified_swift         13     80175.078125
simplified_swift         14     82892.483259
simplified_swift         15     85980.104167
simplified_swift         16     89422.416992
""",
"""
simplified_vegas          2      9376.757812
simplified_vegas          3     14884.322917
simplified_vegas          4     18761.894531
simplified_vegas          5     22858.671875
simplified_vegas          6     27134.960938
simplified_vegas          7     31159.229911
simplified_vegas          8     35204.482422
simplified_vegas          9     39716.128472
simplified_vegas         10     44608.484375
simplified_vegas         11     49582.627841
simplified_vegas         12     54001.881510
simplified_vegas         13     57809.062500
simplified_vegas         14     60879.681920
simplified_vegas         15     65770.182292
simplified_vegas         16     73273.662109
"""]

dfs = []
for output in outputs:
    df_recs = []
    records = output.split('\n')
    for record in records:
        if record == '':
            continue
        split = record.split()
        df_recs.append({
            'cca': split[0],
            'n_flows': int(split[1]),
            'queue_bytes': float(split[2]),
        })
    df = pd.DataFrame(df_recs)
    dfs.append(df)


def func_swift(x, a):
    return a * np.sqrt(x)


def func_vegas(x, a):
    return a * x


fig, ax = plt.subplots()
for df in dfs:
    cca = df['cca'].iloc[0]

    func = func_swift if cca == 'simplified_swift' else func_vegas
    ret = scipy.optimize.curve_fit(func, df['n_flows'], df['queue_bytes'])
    print(cca, ret)

    ax.plot(df['n_flows'], df['queue_bytes'], 'X', label=f'{cca}_data')
    ax.plot(df['n_flows'], func(df['n_flows'], *ret[0]), label=f'{cca}_contract')
    ax.legend()
    ax.grid()
    ax.set_xlabel('Number of Flows')
    ax.set_ylabel('Queue Size [bytes]')
    fig.tight_layout()
    fig.savefig(os.path.join(STORAGE_ROOT, 'fit.svg'))