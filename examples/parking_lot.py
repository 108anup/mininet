import sys

from functools import partial

from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import Node, UserSwitch, OVSKernelSwitch, Controller
from mininet.topo import Topo
from mininet.log import lg, info, setLogLevel
from mininet.util import irange, quietRun
from mininet.link import TCLink

flush = sys.stdout.flush

DURATION = 60


class ParkingLotTopo(Topo):
    def build(self, hops: int, bw_mbps: float, delay_ms: float, **params):
        assert hops >= 1

        # We will have hops+1 pairs of nodes (sender + receiver), and hops+1 switches
        senders = [self.addHost('hs%s' % h) for h in range(hops+1)]
        receivers = [self.addHost('hr%s' % h) for h in range(hops+1)]
        switches = [self.addSwitch('s%s' % s) for s in range(hops+1)]

        next = switches[-1]
        for switch in reversed(switches[:-1]):
            self.addLink(switch, next, bw_netem=bw_mbps)
            next = switch

        self.addLink(senders[0], switches[0])
        self.addLink(receivers[0], switches[-1], delay=f"{delay_ms}ms")
        for i in range(1, hops+1):
            self.addLink(senders[i], switches[i-1])
            self.addLink(receivers[i], switches[i], delay=f"{delay_ms}ms")


def parking_lot_test(hops: int, bw_mbps: float, delay_ms: float, cca: str):

    # TODO: set sysctl

    topo = ParkingLotTopo(hops=hops, bw_mbps=bw_mbps, delay_ms=delay_ms)
    link = TCLink
    net = Mininet(
        topo=topo,
        switch=OVSKernelSwitch,
        controller=Controller,
        link=link,
        waitConnected=True,
    )
    net.start()

    # for h in range(hops+1):
    #     sender = net.get(f'hs{h}')
    #     receiver = net.get(f'hr{h}')
    #     assert isinstance(sender, Node)
    #     assert isinstance(receiver, Node)
    #     receiver.sendCmd(f'iperf3 -s -p 5001 &')
    #     sender.sendCmd(f'iperf3 -c {receiver.IP()} -p 5001 -t {DURATION} --congestion {cca}')

    # TODO: log queue buildup
    CLI(net)

    net.stop()


if __name__ == '__main__':
    hops = 2
    bw_mbps = 10
    delay_ms = 10
    cca = 'reno'
    setLogLevel('info')
    parking_lot_test(hops, bw_mbps, delay_ms, cca)
