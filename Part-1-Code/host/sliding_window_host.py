from abc import ABC

from host.host import Host
from network.network_interface import NetworkInterface
from network.packet import Packet
from simulation.clock import Clock
from util.timeout_calculator import TimeoutCalculator
from util.sliding_window_manager import SlidingWindowManager

"""
This host follows the SlidingWindow protocol. It maintains a window size and the
list of unACKed packets.
"""


class SlidingWindowHost(Host, ABC):

    def __init__(self, clock: Clock, network_interface: NetworkInterface, window_size: int,
                 timeout_calculator: TimeoutCalculator):
        # Host configuration
        self.timeout_calculator: TimeoutCalculator = timeout_calculator
        self.network_interface: NetworkInterface = network_interface
        self.clock: Clock = clock

        # Stateful information you might need to track the progress of this protocol as packets are sent and received.
        self.last_transmitted_sequence_number: int | None = None
        self.sliding_window = SlidingWindowManager(clock=clock, window_size=window_size)
    
    def advance_sequence_number(self) -> int:
        if self.last_transmitted_sequence_number is None:
            self.last_transmitted_sequence_number = 0
        else:
            self.last_transmitted_sequence_number += 1
        return self.last_transmitted_sequence_number

    def run_one_tick(self) -> int | None:
        current_time = self.clock.read_tick()
        # TODO: STEP 1 - Process newly received messages
        #  - These will all be acknowledgement to messages this host has previously sent out.
        #  - You should mark these messages as successfully delivered.
        # You might need to do some operations with the SlidingWindowManager (self.sliding_window)
        # REPLACE pass with your code
        packets_received = self.network_interface.receive_all()
        for packet in packets_received:
            pass 


        # TODO: STEP 2 - Retry any messages that have timed out
        #  - When you transmit each packet (in steps 2 and 3), you should track that message as inflight
        #  - Check to see if there are any inflight messages who's timeout has already passed
        #  - If you find a timed out message, create a new packet and transmit it
        #      - The new packet should have the same sequence number
        #      - You should set the packet's retransmission_flag to true
        #      - The sent time should be the current timestamp
        #      - Use the transmit() function of the network interface to send the packet
        # You might need to do some operations with the SlidingWindowManager (self.sliding_window)
        # REPLACE pass with your code 
        retriable_packets = self.sliding_window.get_packets_to_retry()
        for retriable_message in retriable_packets:
            pass 

        # TODO: STEP 3 - Transmit new messages
        #  - When you transmit each packet (in steps 2 and 3), you should track that message as inflight
        #  - Check to see how many additional packets we can put inflight based on the sliding window spec
        #  - Construct and transmit the packets
        #      - Each new packet represents a new message that should have its own unique sequence number
        #      - Sequence numbers start from 0 and increase by 1 for each new message
        #      - Use the transmit() function of the network interface to send the packet
        # REPLACE pass with your code 
        for i in range(0, self.sliding_window.compute_number_of_packets_to_send()):
            pass

        # STEP 4 - Return
        #  - Return the largest in-order sequence number
        #      - That is, the sequence number such that it, and all sequence numbers before, have been ACKed

        return self.sliding_window.get_largest_in_order_sequence_number()
