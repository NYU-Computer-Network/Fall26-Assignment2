from typing import List

from network.packet import Packet
from simulation.clock import Clock

"""
A class to delay packets by the propagation delay
In our case, we'll use it to delay packets by the two-way propagation delay,
i.e., RTT_min
"""


class DelayBox:

    def __init__(self, clock: Clock,  prop_delay: int):
        self.clock = clock
        # queue of packets being delayed
        self.prop_delay_queue = []
        # how much to delay them by
        self.prop_delay = prop_delay

    def enqueue(self, packets: List[Packet]):
        # enqueue packet after timestamping it
        for packet in packets:
            packet.pdbox_time = self.clock.read_tick()
            packet.ack_flag = True
        self.prop_delay_queue += packets

    def dequeue(self) -> List[Packet]:
        # execute this on every tick
        # packets that are delivered this tick
        to_deliver = []
        for pkt in self.prop_delay_queue:
            # if propagation delay has been exceeded
            if pkt.pdbox_time + self.prop_delay <= self.clock.read_tick():
                assert pkt.pdbox_time + self.prop_delay == self.clock.read_tick()
                to_deliver += [pkt]
        self.prop_delay_queue = [x for x in self.prop_delay_queue if x not in to_deliver]
        return to_deliver
