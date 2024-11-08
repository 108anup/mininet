import os
from typing import Tuple
import pandas as pd
import argparse
import json

import matplotlib.pyplot as plt

from common import parse_tag, plot_df, plot_multi_exp, try_except_wrapper


def parse_tc_df(input_file: str):
    """
    Header:
    time,bytes,packets,drops,overlimits,requeues,backlog,qlen
    """
    df = pd.read_csv(input_file)

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

    return df, ddf


def get_steady_state_bps(df: pd.DataFrame):
    """
    Header is cumulative values:
    time,bytes,packets,drops,overlimits,requeues,backlog,qlen
    """
    # Get average throughput in seconds 25 to 50
    fdf = df[(df['time'] >= 25) & (df['time'] <= 50)]
    send_bytes = fdf['bytes'].iloc[-1] - fdf['bytes'].iloc[0]
    send_time = fdf['time'].iloc[-1] - fdf['time'].iloc[0]
    return send_bytes * 8 / send_time


def parse_tc_summary(input_file):
    df, ddf = parse_tc_df(input_file)
    ss_bps = get_steady_state_bps(df)
    return {
        'ss_bps': ss_bps,
        'ss_mbps': ss_bps / 1e6,
    }


def plot_single_exp(input_file, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    fname = os.path.basename(input_file).replace('.csv', '')
    df, ddf = parse_tc_df(input_file)

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

    plot_df(
        ddf, 'send_rate_mbps', os.path.join(output_dir, f'{fname}-send-rate.svg'),
        xkey='time', xlabel='Time (s)', ylabel='Sent Rate [Mbps]',
    )
    plot_df(
        ddf, 'loss_prob', os.path.join(output_dir, f'{fname}-loss-prob.svg'),
        xkey='time', xlabel='Time (s)', ylabel='Loss Probability',
    )
    # plot_df(
    #     ddf, 'drops_diff', os.path.join(output_dir, f'{fname}-loss.svg'),
    #     xkey='time', xlabel='Time (s)', ylabel='Drops [pkts]',
    # )


def summarize_parking_lot(input_dir, output_dir):
    # find all experiment directories
    # parent of all csv files are experiment directories

    exp_dirs = {}
    for root, _, files in os.walk(input_dir):
        if any([f.endswith('.csv') for f in files]):
            exp_dirs[root] = sorted([f for f in files if f.endswith('.csv')])

    master_records = []
    for exp, files in exp_dirs.items():
        records = []
        tags_exp = parse_tag(os.path.basename(exp))
        for file in files:
            fpath = os.path.join(exp, file)
            record = {}
            summary = parse_tc_summary(fpath)
            record.update(summary)
            tags_flow = parse_tag(file.removesuffix('.csv'))
            record.update(tags_flow)
            records.append(record)

        df = pd.DataFrame(records)
        rdf = df[~df["receiver"].isna()].copy()
        rdf["rid"] = rdf["receiver"].apply(lambda x: x.removeprefix("hr")).astype(int)
        rdf = rdf.sort_values(by='rid')
        ratio = rdf['ss_mbps'].iloc[-1] / rdf['ss_mbps'].iloc[0]
        master_record = {
            "ratio": ratio,
        }
        master_record.update(tags_exp)
        master_records.append(master_record)

    mdf = pd.DataFrame(master_records).sort_values(by=['cca', 'hops'])
    print(mdf)


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
        if args.parking_lot:
            summarize_parking_lot(args.input, args.output)
            # plot_parking_lot(args.input, args.output)
        else:
            plot_multi_exp(args.input, args.output, '.csv', plot_single_exp)
    else:
        plot_single_exp(args.input, args.output)


if(__name__ == "__main__"):
    main()
