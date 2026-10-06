# Required for dropping packets at random
import queue
import random
from typing import List

from network.packet import Packet
from simulation import simulation_logger as log

"""
A class to represent a link with a finite capacity of 1 packet per tick
We can generalize this to other capacities, but we're keeping the assignment simple
"""


class Link:

    def __init__(self, loss_ratio, queue_limit, verbose=True):
        # queue of packets at the link
        self.link_queue = queue.Queue()
        # probability of dropping packets when link dequeues them
        self.loss_ratio = loss_ratio
        # Max size of queue in packets
        self.queue_limit = queue_limit
        # Whether to print statements
        self.verbose = verbose

    """
    Function to receive packets from a device connected at either
    ends of the link. Device here can represent an end host or any other
    network device.

    The device connected to the link needs to call the enqueue function to put
    packet on to the link. If link's queue is full, it starts dropping packets
    and does not receive any more packets.
    """

    def enqueue(self, packets: List[Packet]):
        for packet in packets:
            if self.link_queue.qsize() < self.queue_limit:
                self.link_queue.put(packet)  # append to the queue
            else:
                log.add_event(type="Buffer capacity exceeded", desc=f"Dropping packet, Sequence number: {packet.sequence_number}")

    """
    This function dequeues the packets that should leave the link during this tick and returns them.
    """

    def dequeue(self) -> List[Packet]:
        packets_to_dequeue = []

        # Execute on every tick
        # Dequeue from link queue if queue is not empty
        if self.link_queue.qsize() != 0:
            head = self.link_queue.get()
            if random.uniform(0.0, 1) < (1 - self.loss_ratio):
                # dequeue and send to prop delay box
                packets_to_dequeue.append(head)
            else:
                log.add_event(type="Randomly dropping data in network", desc=f"Sequence number: {head.sequence_number}")

        return packets_to_dequeue
