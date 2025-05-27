#!/usr/bin/env python

import argparse
import json
import math
import os
import shutil
import sys
import time
from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd

from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.net import Mininet
from mininet.node import Controller, Node, OVSKernelSwitch
from mininet.topo import Topo

flush = sys.stdout.flush

INTER_POLL_TIME = 1e-1  # seconds
DURATION = 60  # seconds
LIVELOG_ROOT = '/home/mininet/P/logs/'
STORAGE_ROOT = '/home/mininet/P/CCmatic-experiments/data/mininet/parking_lot'
PKT_SIZE_BYTES = 1500
TC_RECORD_HEADER = f"time,bytes,packets,drops,overlimits,requeues,backlog,qlen\n"
GENERICCC_PATH = '/home/mininet/P/genericCC'
ICC_PATH = '/home/mininet/P/icc'
ASTRAEA_PATH = '/home/mininet/P/contracts/astraea-open-source'


def get_queue_size_pkts(bw_mbps: float, delay_ms: float, queue_size_bdp: float) -> int:
    bdp_bytes = 2 * bw_mbps * delay_ms * 1e3 / 8
    queue_size = math.ceil(queue_size_bdp * bdp_bytes / PKT_SIZE_BYTES)
    return queue_size


class ParkingLotTopo(Topo):
    def build(self, hops: int, bw_mbps: float, delay_ms: float, queue_size_bdp: float, **params):
        assert hops >= 1
        queue_size: int = get_queue_size_pkts(bw_mbps, delay_ms, queue_size_bdp)

        # We will have hops+1 pairs of nodes (sender + receiver), and hops+1 switches
        senders = [self.addHost('hs%s' % h) for h in range(hops+1)]
        receivers = [self.addHost('hr%s' % h) for h in range(hops+1)]
        switches = [self.addSwitch('s%s' % s) for s in range(hops+1)]

        next = switches[-1]
        for switch in reversed(switches[:-1]):
            self.addLink(switch, next, bw_netem=bw_mbps, max_queue_size=queue_size)
            next = switch

        self.addLink(senders[0], switches[0])
        self.addLink(switches[-1], receivers[0], delay=f"{delay_ms}ms")
        for i in range(1, hops+1):
            self.addLink(senders[i], switches[i-1])
            self.addLink(switches[i], receivers[i], delay=f"{delay_ms}ms")


def get_livelog_name_path(sender: Node, receiver: Node) -> Tuple[str, str]:
        lname = f'[s={sender}][r={receiver}].json'
        llpath = os.path.join(LIVELOG_ROOT, lname)
        return lname, llpath


def get_tc_record(node: Node, intf_name: str, start: float) -> list:
    # info("Trying to fetch stats from node: %s for intf: %s\n" % (node, intf_name))
    stats: str = node.cmd(f'tc -s -j qdisc show dev {intf_name}')  # type: ignore
    jdict = json.loads(stats)
    record = [
        time.time() - start,
        jdict[0]['bytes'],
        jdict[0]['packets'],
        jdict[0]['drops'],
        jdict[0]['overlimits'],
        jdict[0]['requeues'],
        jdict[0]['backlog'],
        jdict[0]['qlen'],
    ]
    return record


def run_iperf_test(
    net: Mininet,
    senders: List[Node],
    receivers: List[Node],
    switches: List[OVSKernelSwitch],
    cca: str,
    experiment_path: str,
    rtprop: float,
):
    assert len(senders) == len(receivers)
    n = len(senders)
    os.makedirs(LIVELOG_ROOT, exist_ok=True)

    if "ndd" in cca:
        lname, llpath = get_livelog_name_path(senders[0], receivers[0])
        dlog, dlpath = lname.replace(".json", ".dmesg"), llpath.replace(
            ".json", ".dmesg"
        )
        if os.path.exists(dlpath):
            os.remove(dlpath)

        senders[0].cmd("sudo dmesg --clear")
        senders[0].cmd(f"dmesg --level info --follow --notime 1> {dlpath} 2>&1 &")

    info('*** Starting iperf3 test\n')
    for i in range(n):
        sender = senders[i]
        receiver = receivers[i]

        lname, llpath = get_livelog_name_path(sender, receiver)
        if os.path.exists(llpath):
            os.remove(llpath)

        if "genericcc_" in cca:
            short_cca = cca.replace("genericcc_", "")
            cc_params = ""
            if short_cca == 'markovian':
                # cc_params = "delta_conf=do_ss:auto:0.5"
                cc_params = "delta_conf=do_ss:constant_delta:0.1"

            receiver.sendCmd(f'{GENERICCC_PATH}/receiver 5001')
            sender_log = os.path.join(LIVELOG_ROOT, f'[sender={sender}].txt')
            sender.cmd(f"export MIN_RTT={rtprop}")
            sender.sendCmd(
                f"MIN_RTT={rtprop} "
                f"{GENERICCC_PATH}/sender serverip={receiver.IP()} serverport=5001 "
                f"offduration=0 onduration={int(DURATION*1e3)} "
                f"cctype={short_cca} "
                f"{cc_params} "
                f"traffic_params=deterministic,num_cycles=1 > {sender_log} 2>&1 "
            )

        elif "icc" in cca:
            receiver.sendCmd(f'{ICC_PATH}/receiver 5001')
            sender_log = os.path.join(LIVELOG_ROOT, f'[sender={sender}].txt')
            sender.sendCmd(
                f"{ICC_PATH}/sender serverip={receiver.IP()} serverport=5001 "
                f"offduration=0 onduration={int(DURATION*1e3)} "
                f"cctype=icc lamda_conf=do_ss:compete:auto_theta:auto:1 Bd_conf=10 Rc_conf=30 "
                f"traffic_params=deterministic,num_cycles=1 > {sender_log} 2>&1 "
            )

        elif "astraea" in cca:
            receiver.sendCmd(f"{ASTRAEA_PATH}/src/build/bin/server --port=5001")
            cmd = f"{ASTRAEA_PATH}/src/build/bin/client_eval --ip={receiver.IP()} \
                  --port=5001 \
                  --cong=astraea \
                  --interval=30 \
                  --pyhelper={ASTRAEA_PATH}/python/infer.py \
                  --model={ASTRAEA_PATH}/models/py/ "
            sender.sendCmd(f"{cmd}")

        else:
            receiver.sendCmd(f'iperf3 -s -p 5001 > /dev/null')
            sender.sendCmd(
                f"iperf3 -c {receiver.IP()} -p 5001 -t {DURATION}"
                f" --congestion {cca} --json --logfile {llpath}"
            )
        # time.sleep(5)

    @dataclass
    class TcLogNode:
        node: Node
        intf_name: str
        logfile: str

        def __post_init__(self):
            self.logfile_handler = open(self.logfile, 'w')
            self.logfile_handler.write(TC_RECORD_HEADER)

    # Log all but last switch
    loggables = []
    for i, s in enumerate(switches[:-1]):
        l = os.path.join(LIVELOG_ROOT, f'[switch={s}].csv')
        intf_name = net.linksBetween(net.switches[i], net.switches[i+1])[0].intf1.name
        loggables.append(TcLogNode(s, intf_name, l))

    # Log all senders and receivers
    for i in range(n):
        # sender = senders[i]
        # l = os.path.join(LIVELOG_ROOT, f'[sender={sender}].csv')
        # # Since sender/receiver are busy with sending, we log corresponding
        # # interfaces on the switches
        # intf = sender.intfList()[0]
        # switch = intf.link.intf2.node
        # intf_name = intf.link.intf2.name
        # loggables.append(TcLogNode(switch, intf_name, l))

        receiver = receivers[i]
        l = os.path.join(LIVELOG_ROOT, f'[receiver={receiver}].csv')
        intf = receiver.intfList()[0]
        switch = intf.link.intf1.node
        intf_name = intf.link.intf1.name
        loggables.append(TcLogNode(switch, intf_name, l))

    start = time.time()
    while time.time() - start < DURATION:
        for loggable in loggables:
            record = get_tc_record(loggable.node, loggable.intf_name, start)
            loggable.logfile_handler.write(','.join(map(str, record)) + '\n')
        time.sleep(INTER_POLL_TIME)

    for loggable in loggables:
        loggable.logfile_handler.close()

    # Wait for all iperf3 to finish
    for sender in senders:
        if cca == "astraea":
            sender.sendInt()
        sender.waitOutput()
    for reciever in receivers:
        # reciever.sendCmd('killall iperf3')
        reciever.sendInt()
        reciever.waitOutput()

    # Copy all logs to storage
    os.makedirs(experiment_path, exist_ok=True)

    if "genericcc_" not in cca and cca not in ["astraea", "icc"]:
        # iperf json logs (1s)
        for i in range(n):
            sender = senders[i]
            receiver = receivers[i]
            lname, llpath = get_livelog_name_path(sender, receiver)
            slpath = os.path.join(experiment_path, lname)
            shutil.copy(llpath, slpath)

    if "ndd" in cca:
        senders[0].cmd("sudo killall dmesg")
        lname, llpath = get_livelog_name_path(senders[0], receivers[0])
        dlog, dlpath = lname.replace(".json", ".dmesg"), llpath.replace(
            ".json", ".dmesg"
        )
        shutil.copy(dlpath, os.path.join(experiment_path, dlog))

    # TC logs (100ms)
    for loggable in loggables:
        lpath = os.path.join(experiment_path, os.path.basename(loggable.logfile))
        shutil.copy(loggable.logfile, lpath)

    info('*** iperf3 test completed\n')


def parking_lot_test(hops: int, bw_mbps: float, delay_ms: float, queue_size_bdp: float, cca: str):

    # TODO: set sysctl

    topo = ParkingLotTopo(hops=hops, bw_mbps=bw_mbps, delay_ms=delay_ms, queue_size_bdp=queue_size_bdp)
    link = TCLink
    net = Mininet(
        topo=topo,
        switch=OVSKernelSwitch,
        controller=Controller,
        link=link,
        waitConnected=True,
    )
    net.start()

    senders: List[Node] = [net.get(f'hs{h}') for h in range(hops+1)]  # type: ignore
    receivers: List[Node] = [net.get(f'hr{h}') for h in range(hops+1)]  # type: ignore
    switches: List[OVSKernelSwitch] = [net.get(f's{s}') for s in range(hops+1)]  # type: ignore
    experiment_dir = f'[hops={hops}][bw_mbps={bw_mbps}][delay_ms={delay_ms}][queue_size_bdp={queue_size_bdp}][cca={cca}]'
    experiment_path = os.path.join(STORAGE_ROOT, f"[bw_mbps={bw_mbps}][delay_ms={delay_ms}][queue_size_bdp={queue_size_bdp}][cca={cca}]", experiment_dir)

    # CLI(net)
    run_iperf_test(net, senders, receivers, switches, cca, experiment_path, 2 * delay_ms)

    # Quick printing of result
    ratio = 1.0
    if "genericcc_" not in cca and cca not in ["astraea", "icc"]:
        throughputs = []
        for h in range(hops+1):
            sender = senders[h]
            receiver = receivers[h]
            lname, llpath = get_livelog_name_path(sender, receiver)

            with open(llpath, 'r') as f:
                data = json.load(f)
                throughput = float(data["end"]["sum_received"]["bits_per_second"]) / 1e6
                sender = senders[h]
                receiver = receivers[h]
                info(f'*** {sender} -> {receiver} throughput: {throughput:.6f} Mbps\n')
                throughputs.append(throughput)

        ratio = throughputs[-1]/throughputs[0]

    info(f"*** Parking log experiment result: Hops={hops}, Ratio={ratio:.2f}\n")

    net.stop()
    return ratio


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o', '--output', default=STORAGE_ROOT,
        type=str, action='store',
        help='path output dir')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    STORAGE_ROOT = args.output

    hops = 3
    bw_mbps = 10
    delay_ms = 15  # one way
    cca = 'cubic'
    queue_size_bdp = 100
    # queue_size_bdp = 1

    INTER_POLL_TIME = max(INTER_POLL_TIME, delay_ms / 1e3)
    setLogLevel('info')

    records = []
    # for hops in [3]:
    # for cca in ["reno", "cubic", "genericcc_markovian", "vegas"]:
    # for cca in ["ndd", "bbr", "reno", "cubic"]:
    for cca in ["icc"]:
        for hops in [2]:
        # for hops in range(1, 9):
            ratio = parking_lot_test(hops, bw_mbps, delay_ms, queue_size_bdp, cca)
            records.append({
                'hops': hops,
                'ratio': ratio,
            })
        df = pd.DataFrame(records)
        info(f"{cca}\n")
        info(df)
        info("\n")
