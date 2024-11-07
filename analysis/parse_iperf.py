import os
import pandas as pd
import argparse
import json

import matplotlib.pyplot as plt

from common import parse_tag, plot_df, plot_multi_exp, try_except_wrapper


def get_steady_state_bps(df: pd.DataFrame):
    """
    Intervals are roughly 1 seconds long.
    df has one row for each interval.

    Assuming experiment is 60 seconds long.
    We want average throughput in intervals 30 to 40.
    """

    df["data_bits"] = df["bits_per_second"] * df["seconds"]
    fdf = df[(df['start'] >= 25) & (df['end'] <= 50)]
    return fdf["data_bits"].sum() / fdf["seconds"].sum()


def parse_jdict(fpath):
    with open(fpath, 'r') as f:
        try:
            jdict = json.load(f)
        except json.decoder.JSONDecodeError as e:
            print(f"ERROR: json decode error for file: {fpath}")
            print(e)
            raise e
    return jdict


def parse_iperf_summary(fpath):
    jdict = parse_jdict(fpath)

    ret = {
        'min_rtt': jdict['end']['streams'][0]['sender']['min_rtt'],
        'max_rtt': jdict['end']['streams'][0]['sender']['max_rtt'],
        'mean_rtt': jdict['end']['streams'][0]['sender']['mean_rtt'],
        'bits_per_second': jdict['end']['streams'][0]['receiver'][
            'bits_per_second'
        ],
        'retransmits': jdict['end']['streams'][0]['sender']['retransmits'],
        'time_seconds': jdict['end']['streams'][0]['sender']['seconds'],
    }
    ret['mbps'] = ret['bits_per_second'] / 1e6
    return ret


def parse_iperf_timeseries(fpath):
    jdict = parse_jdict(fpath)

    records = [
        {
            'start': record['streams'][0]['start'],
            'end': record['streams'][0]['end'],
            'seconds': record['streams'][0]['seconds'],
            'bits_per_second': record['streams'][0][
                'bits_per_second'
            ],
            'retransmits': record['streams'][0]['retransmits'],
            'rtt': record['streams'][0]['rtt'],
        }
        for record in jdict['intervals']
    ]
    return pd.DataFrame(records).sort_values(by='start')


def plot_single_exp(input_file, output_dir):
    fname = os.path.basename(input_file).replace('.json', '')
    df = parse_iperf_timeseries(input_file)
    df['mbps'] = df['bits_per_second'] / 1e6

    os.makedirs(output_dir, exist_ok=True)
    plot_df(df, 'retransmits',
            os.path.join(output_dir, f'{fname}_iperf_retransmits.svg'),
            xkey='end', xlabel='Time (s)',
            ylabel='# Retransmits',
            title=os.path.basename(input_file))
    plot_df(df, 'mbps',
            os.path.join(output_dir, f'{fname}_iperf_throughput.svg'),
            xkey='end', xlabel='Time (s)',
            ylabel='Throughput (Mbps)',
            title=os.path.basename(input_file),
            ylim=(0, None))

    summary = parse_iperf_summary(input_file)
    print(input_file)
    print(summary)


def summarize_parking_lot(input_dir, output_dir):
    # find all experiment directories
    # parent of all json files are experiment directories

    exp_dirs = {}
    for root, _, files in os.walk(input_dir):
        if any([f.endswith('.json') for f in files]):
            exp_dirs[root] = sorted([f for f in files if f.endswith('.json')])

    master_records = []
    for exp, files in exp_dirs.items():
        records = []
        tags_exp = parse_tag(os.path.basename(exp))
        for file in files:
            fpath = os.path.join(exp, file)
            record = {}
            summary = parse_iperf_summary(fpath)
            record.update(summary)
            df = parse_iperf_timeseries(fpath)
            ss_bps = get_steady_state_bps(df)
            record['ss_bps'] = ss_bps
            record['ss_mbps'] = ss_bps / 1e6
            tags_flow = parse_tag(file.removesuffix('.json'))
            record.update(tags_flow)
            records.append(record)

        rdf = pd.DataFrame(records).sort_values(by='s')
        ratio = rdf['ss_mbps'].iloc[-1] / rdf['ss_mbps'].iloc[0]
        master_record = {
            "ratio": ratio,
        }
        master_record.update(tags_exp)
        master_records.append(master_record)

    mdf = pd.DataFrame(master_records).sort_values(by='hops')
    print(mdf)


# def plot_parking_lot(input_dir, output_dir):
#     input_files = []
#     for root, _, files in os.walk(input_dir):
#         for filename in files:
#             if (filename.endswith('.json')):
#                 input_files.append(os.path.join(root, filename))
#     input_files = sorted(input_files)

#     dfs = [parse_iperf_timeseries(f) for f in input_files]
#     for df in dfs:
#         df['mbps'] = df['bits_per_second'] / 1e6

#     exp = parse_exp_raw(os.path.basename(input_files[0]).removesuffix('.json'))
#     print_info = [str(int(exp["rate"]) * 12)]

#     os.makedirs(output_dir, exist_ok=True)
#     n = len(dfs)
#     rates = []
#     fig, ax = plt.subplots(n, 1, figsize=(6.4, 4.8*1.5), sharex=True, sharey=True)
#     for i, df in enumerate(dfs):
#         exp = parse_exp_raw(os.path.basename(input_files[i]).removesuffix('.json'))
#         summary = parse_iperf_summary(input_files[i])
#         title = "flow_id={}, throughput={:.2f} mbps".format(int(exp['port']), summary['mbps'])
#         ax[i].set_title(title)
#         ax[i].plot(df['end'], df['mbps'])
#         ax[i].set_ylabel('Throughput (Mbps)')
#         ax[i].grid(True)

#         print_info.append("{:.2f}".format(summary['mbps']))
#         rates.append(summary['mbps'])

#     ax[-1].set_xlabel('Time (s)')
#     fig.set_tight_layout(True)
#     fig.savefig(os.path.join(output_dir, 'iperf_parking_lot.png'))
#     print_info.append("{:.2f}".format(max(rates) / min(rates)))
#     print("\t".join(print_info))


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
            plot_multi_exp(args.input, args.output, '.json', plot_single_exp)
    else:
        plot_single_exp(args.input, args.output)


if(__name__ == "__main__"):
    main()
