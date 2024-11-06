#!/usr/bin/env python

import json
from math import log
import math
import os
import shutil
import sys
import time
from typing import List, Tuple
import pandas as pd

from functools import partial

from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import Node, UserSwitch, OVSKernelSwitch, Controller
from mininet.topo import Topo
from mininet.log import lg, info, setLogLevel
from mininet.util import ensureRoot, irange, quietRun
from mininet.link import TCLink

flush = sys.stdout.flush

INTER_POLL_TIME = 5e-3  # seconds
DURATION = 60
LIVELOG_ROOT = '/home/mininet/P/logs/'
STORAGE_ROOT = '/home/mininet/P/CCmatic-experiments/data/mininet'
PKT_SIZE_BYTES = 1500


def get_queue_size_pkts(bw_mbps: float, delay_ms: float, queue_size_bdp: float) -> int:
    bdp_bytes = bw_mbps * delay_ms * 1e3 / 8
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
        self.addLink(receivers[0], switches[-1], delay=f"{delay_ms}ms")
        for i in range(1, hops+1):
            self.addLink(senders[i], switches[i-1])
            self.addLink(receivers[i], switches[i], delay=f"{delay_ms}ms")


def run_iperf_test(
    net: Mininet,
    senders: List[Node],
    receivers: List[Node],
    switches: List,
    cca: str,
    experiment_path: str,
):
    assert len(senders) == len(receivers)
    n = len(senders)

    def get_livelog_name_path(sender: Node, receiver: Node) -> Tuple[str, str]:
        lname = f'[s={sender}][r={receiver}].json'
        llpath = os.path.join(LIVELOG_ROOT, lname)
        return lname, llpath

    info('*** Starting iperf3 test\n')
    for i in range(n):
        sender = senders[i]
        receiver = receivers[i]

        lname, llpath = get_livelog_name_path(sender, receiver)
        if os.path.exists(llpath):
            os.remove(llpath)

        receiver.sendCmd(f'iperf3 -s -p 5001 > /dev/null')
        sender.sendCmd(
            f"iperf3 -c {receiver.IP()} -p 5001 -t {DURATION}"
            f" --congestion {cca} --json --logfile {llpath}"
        )

    # Log all switches
    switch_logfiles = [
        os.path.join(LIVELOG_ROOT, f'[switch={s}].log') for s in switches
    ]
    for sl in switch_logfiles:
        if os.path.exists(sl):
            os.remove(sl)

    start = time.time()
    while time.time() - start < DURATION:
        for i, switch in enumerate(switches):
            intf_name = net.linksBetween(net.switches[i], net.switches[i+1])[0].intf1.name
            switch.sendCmd(f'tc -s qdisc show dev {intf_name} >> {switch_logfiles[i]}')
        time.sleep(INTER_POLL_TIME)

    # Wait for all iperf3 to finish
    for sender in senders:
        sender.waitOutput()
    for reciever in receivers:
        # reciever.sendCmd('killall iperf3')
        reciever.sendInt()
        reciever.waitOutput()

    # Move all logs to storage
    os.makedirs(experiment_path, exist_ok=True)

    for i in range(n):
        sender = senders[i]
        receiver = receivers[i]
        lname, llpath = get_livelog_name_path(sender, receiver)
        slpath = os.path.join(experiment_path, lname)
        shutil.copy(llpath, slpath)

    for sl in switch_logfiles:
        slpath = os.path.join(experiment_path, os.path.basename(sl))
        shutil.copy(sl, slpath)

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
    experiment_path = os.path.join(STORAGE_ROOT, "parking_lot", experiment_dir)

    run_iperf_test(net, senders, receivers, switches, cca, experiment_path)


    throughputs = []
    for h in range(hops+1):
        sender = senders[h]
        receiver = receivers[h]
        livelog_name = f'[s={sender}][r={receiver}].json'
        livelog_path = os.path.join(LIVELOG_ROOT, livelog_name)
        log_path = os.path.join(experiment_path, livelog_name)
        shutil.copy(livelog_path, log_path)

        with open(livelog_path, 'r') as f:
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


if __name__ == '__main__':
    hops = 3
    bw_mbps = 100
    delay_ms = 50  # one way
    cca = 'reno'
    queue_size_bdp = 1

    setLogLevel('info')

    records = []
    for hops in [3]:
    # for hops in range(9, 11):
        ratio = parking_lot_test(hops, bw_mbps, delay_ms, queue_size_bdp, cca)
        records.append({
            'hops': hops,
            'ratio': ratio,
        })
    df = pd.DataFrame(records)
    info(df)
    info("\n")
