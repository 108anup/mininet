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

INTER_POLL_TIME = 1e-1  # seconds
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


def get_livelog_name_path(sender: Node, receiver: Node) -> Tuple[str, str]:
        lname = f'[s={sender}][r={receiver}].json'
        llpath = os.path.join(LIVELOG_ROOT, lname)
        return lname, llpath


def run_iperf_test(
    net: Mininet,
    senders: List[Node],
    receivers: List[Node],
    switches: List[OVSKernelSwitch],
    cca: str,
    experiment_path: str,
):
    assert len(senders) == len(receivers)
    n = len(senders)

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

    # Log all but last switch
    switch_logfiles = []
    switch_logfile_handlers = []
    for s in switches[:-1]:
        sl = os.path.join(LIVELOG_ROOT, f'[switch={s}].csv')
        switch_logfiles.append(sl)
        slf = open(sl, 'w')
        switch_logfile_handlers.append(slf)
        slf.write(f"time,bytes,packets,drops,overlimits,requeues,backlog,qlen\n")

    start = time.time()
    while time.time() - start < DURATION:
        for i, switch in enumerate(switches[:-1]):
            intf_name = net.linksBetween(net.switches[i], net.switches[i+1])[0].intf1.name
            stats: str = switch.cmd(f'tc -s -j qdisc show dev {intf_name}')  # type: ignore
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
            switch_logfile_handlers[i].write(','.join(map(str, record)) + '\n')
        time.sleep(INTER_POLL_TIME)

    for slf in switch_logfile_handlers:
        slf.close()

    # Wait for all iperf3 to finish
    for sender in senders:
        sender.waitOutput()
    for reciever in receivers:
        # reciever.sendCmd('killall iperf3')
        reciever.sendInt()
        reciever.waitOutput()

    # Copy all logs to storage
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
    experiment_path = os.path.join(STORAGE_ROOT, "parking_lot", f"[cca={cca}]", experiment_dir)

    run_iperf_test(net, senders, receivers, switches, cca, experiment_path)

    # Quick printing of result
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


if __name__ == '__main__':
    hops = 3
    bw_mbps = 400
    delay_ms = 1  # one way
    cca = 'reno'
    queue_size_bdp = 1

    INTER_POLL_TIME = max(INTER_POLL_TIME, delay_ms / 1e3)
    setLogLevel('info')

    records = []
    # for hops in [3]:
    for hops in range(2, 11):
        ratio = parking_lot_test(hops, bw_mbps, delay_ms, queue_size_bdp, cca)
        records.append({
            'hops': hops,
            'ratio': ratio,
        })
    df = pd.DataFrame(records)
    info(df)
    info("\n")
