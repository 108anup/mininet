import os
import pandas as pd
import argparse
import json

import matplotlib.pyplot as plt

from common import parse_tag, plot_df, plot_multi_exp, try_except_wrapper


def plot_single_exp(input_file, output_dir):
    fname = os.path.basename(input_file).replace('.csv', '')
    df = pd.read_csv(input_file)
    os.makedirs(output_dir, exist_ok=True)
    """
    Header:
    time,bytes,packets,drops,overlimits,requeues,backlog,qlen
    """
    # plot_df(
    #     df, 'bytes', os.path.join(output_dir, f'{fname}-sent.svg'),
    #     xkey='time', xlabel='Time (s)', ylabel='Sent [bytes]',
    # )
    plot_df(
        df, 'qlen', os.path.join(output_dir, f'{fname}-queue.svg'),
        xkey='time', xlabel='Time (s)', ylabel='Queue [pkts]',
    )
    # plot_df(
    #     df, 'drops', os.path.join(output_dir, f'{fname}-loss.svg'),
    #     xkey='time', xlabel='Time (s)', ylabel='Drops [pkts]',
    # )

    # window metrics
    # bucket = '100'
    # df['time'] = pd.to_datetime(df['time'], unit='s')
    # df.set_index('time', inplace=True)
    # ddf = df.resample(bucket).last().dropna()
    # ddf.reset_index(inplace=True)
    ddf = df

    ddf["bytes_diff"] = ddf["bytes"].diff()
    ddf["packets_diff"] = ddf["packets"].diff()
    ddf["drops_diff"] = ddf["drops"].diff()
    ddf["time_diff"] = ddf["time"].diff()

    ddf['send_rate_mbps'] = ddf['bytes_diff'] / ddf['time_diff'] * 8 / 1e6
    ddf['loss_prob'] = ddf['drops_diff'] / ddf['packets_diff']

    plot_df(
        ddf, 'send_rate_mbps', os.path.join(output_dir, f'{fname}-send-rate.svg'),
        xkey='time', xlabel='Time (s)', ylabel='Sent Rate [Mbps]',
    )
    plot_df(
        ddf, 'loss_prob', os.path.join(output_dir, f'{fname}-loss-prob.svg'),
        xkey='time', xlabel='Time (s)', ylabel='Loss Probability',
    )
    plot_df(
        ddf, 'drops_diff', os.path.join(output_dir, f'{fname}-loss.svg'),
        xkey='time', xlabel='Time (s)', ylabel='Drops [pkts]',
    )

@try_except_wrapper
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i', '--input', required=True,
        type=str, action='store',
        help='path to mahimahi trace')
    parser.add_argument(
        '-o', '--output', required=True,
        type=str, action='store',
        help='path output figure')
    parser.add_argument(
        '--parking-lot', required=False,
        action='store_true',
        help='plot parking lot')
    args = parser.parse_args()

    if(os.path.isdir(args.input)):
        plot_multi_exp(args.input, args.output, '.csv', plot_single_exp)
        # if args.parking_lot:
        #     plot_parking_lot(args.input, args.output)
    else:
        plot_single_exp(args.input, args.output)


if(__name__ == "__main__"):
    main()
