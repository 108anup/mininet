import os
import pandas as pd
import argparse
import json

import matplotlib.pyplot as plt

from common import parse_tag, plot_df, plot_multi_exp, try_except_wrapper


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
        plot_multi_exp(args.input, args.output, '.json', plot_single_exp)
        # if args.parking_lot:
        #     plot_parking_lot(args.input, args.output)
    else:
        plot_single_exp(args.input, args.output)


if(__name__ == "__main__"):
    main()
