#!/usr/bin/env python

import json
from math import log
import math
import os
import shutil
import sys
from typing import List
import pandas as pd
import numpy as np

from functools import partial

from examples.parking_lot import LIVELOG_ROOT, STORAGE_ROOT, get_queue_size_pkts, run_iperf_test
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import Node, UserSwitch, OVSKernelSwitch, Controller
from mininet.topo import Topo
from mininet.log import lg, info, setLogLevel
from mininet.util import ensureRoot, irange, quietRun
from mininet.link import TCLink

flush = sys.stdout.flush

class DumbbellTopo(Topo):
    def build(self, n_flows: int, bw_mbps: float, delay_ms: float, queue_size_bdp: float, **params):
        assert n_flows >= 1
        queue_size: int = get_queue_size_pkts(bw_mbps, delay_ms, queue_size_bdp)

        senders = [self.addHost('hs%s' % h) for h in range(n_flows+1)]
        receivers = [self.addHost('hr%s' % h) for h in range(n_flows+1)]
        switches = [self.addSwitch('s%s' % s) for s in range(2)]

        next = switches[-1]
        for switch in reversed(switches[:-1]):
            self.addLink(switch, next, bw_netem=bw_mbps, max_queue_size=queue_size)
            next = switch

        for i in range(n_flows):
            self.addLink(senders[i], switches[0])
            self.addLink(switches[1], receivers[i], delay=f"{delay_ms}ms")


def dumbbell_test(n_flows: int, bw_mbps: float, delay_ms: float, queue_size_bdp: float, cca: str):

    topo = DumbbellTopo(n_flows=n_flows, bw_mbps=bw_mbps, delay_ms=delay_ms, queue_size_bdp=queue_size_bdp)
    link = TCLink
    net = Mininet(
        topo=topo,
        switch=OVSKernelSwitch,
        controller=Controller,
        link=link,
        waitConnected=True,
    )
    net.start()

    senders: List[Node] = [net.get(f'hs{h}') for h in range(n_flows)]  # type: ignore
    receivers: List[Node] = [net.get(f'hr{h}') for h in range(n_flows)]  # type: ignore

    run_iperf_test(net, senders, receivers, cca)

    experiment_dir = f'[n_flows={n_flows}][bw_mbps={bw_mbps}][delay_ms={delay_ms}][queue_size_bdp={queue_size_bdp}][cca={cca}]'
    experiment_path = os.path.join(STORAGE_ROOT, "parking_lot", experiment_dir)
    os.makedirs(experiment_path, exist_ok=True)

    throughputs = []
    for h in range(n_flows):
        sender = senders[h]
        receiver = receivers[h]
        livelog_name = f'[s={sender}][r={receiver}].json'
        livelog_path = os.path.join(LIVELOG_ROOT, livelog_name)
        log_path = os.path.join(experiment_path, livelog_name)
        shutil.copy(livelog_path, log_path)
        # TODO: copy the log in the iperf test itself.

        with open(livelog_path, 'r') as f:
            data = json.load(f)
            throughput = float(data["end"]["sum_received"]["bits_per_second"]) / 1e6
            sender = senders[h]
            receiver = receivers[h]
            info(f'*** {sender} -> {receiver} throughput: {throughput:.6f} Mbps\n')
            throughputs.append(throughput)

    # CLI(net)
    avg = np.mean(throughputs)
    info(f"*** Dumbbell experiment result: n_flows={n_flows}, Avg throughput={avg:.6f} Mbps\n")

    net.stop()
    return avg


if __name__ == '__main__':
    bw_mbps = 100
    delay_ms = 50  # one way
    cca = 'vegas'
    queue_size_bdp = 1

    setLogLevel('info')

    records = []
    # for hops in [3]:
    for n_flows in range(1, 11):
        ratio = dumbbell_test(n_flows, bw_mbps, delay_ms, queue_size_bdp, cca)
        records.append({
            'n_flows': n_flows,
            'ratio': ratio,
        })
    df = pd.DataFrame(records)
    info(df)
    info("\n")
