from typing import List

from .packet import Packet
from simulation.clock import Clock
import simulation.simulation_logger as log

"""
Network Interface
=================

These functions can be used by the host as an interface to the network.
The host can send messages by calling transmit.
The packet will then be added to the network interface's buffer, who will then flush that buffer to the simulation.
Similarly, the simulation will send messages destined for your host to this buffer.
The host can then call receive to get all messages destined for it that are currently buffered.
"""


class NetworkInterface:

    def __init__(self, clock: Clock):
        self.clock = clock
        self.next_sequence_number = 0
        self.transmission_buffer: List[Packet] = []
        self.receive_buffer: List[Packet] = []

    """
    Place a packet on the egress buffer.
    This will then be sent out to the network during the tick execution.
    """
    def transmit(self, packet: Packet):
        if not packet.retransmission_flag:
            log.add_event(type="Transmit", desc=f"Sequence number: {packet.sequence_number}")
        else:
            log.add_event(type="Retransmit", desc=f"Sequence number: {packet.sequence_number}")
        self.transmission_buffer.append(packet)

    """
    Retrieve all packets currently on the ingress buffer
    """
    def receive_all(self) -> List[Packet]:
        packets = self.receive_buffer
        self.receive_buffer = []
        for packet in packets:
            log.add_event(type="Receive", desc=f"Sequence number: {packet.sequence_number}")
        return packets

    """
    This function should only be used by the simulation to pull packets from the egress buffer to send them out to the network.
    You shouldn't need to call this directly. It's an implementation detail of this simulator.
    """
    def pull_packets_from_network_interface(self) -> List[Packet]:
        packets = self.transmission_buffer
        self.transmission_buffer = []
        return packets

    """
    This function should only be used by the simulation to push packets to the ingress buffer from the network.
    You shouldn't need to call this directly. It's an implementation detail of this simulator.
    """
    def push_packets_to_network_interface(self, packets: List[Packet]):
        self.receive_buffer.extend(packets)
