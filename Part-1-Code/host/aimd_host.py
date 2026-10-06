from typing import List
from matplotlib import pyplot as plt

from network.network_interface import NetworkInterface
from simulation.clock import Clock
from util.timeout_calculator import TimeoutCalculator
from simulation import simulation_logger as log
from network.packet import Packet
from util.sliding_window_manager import SlidingWindowManager 
"""
This class implements a host that follows the AIMD protocol.
"""


class AimdHost:

    def __init__(self, clock: Clock, network_interface: NetworkInterface, timeout_calculator: TimeoutCalculator):
        # Host configuration
        self.timeout_calculator: TimeoutCalculator = timeout_calculator
        self.network_interface: NetworkInterface = network_interface
        self.clock: Clock = clock

        # Stateful information you might need to track the progress of this protocol as packets are
        #  sent and received. Your sliding window should be initialized to a size of 1, and should use the slow start
        #  algorithm until you hit your first timeout
        #    - Feel free to create new variables and classes, just don't delete any existing infrastructure.
        #    - In particular, you should make use of the network interface to interact with the network.

        self.last_transmitted_sequence_number: int | None = None
        self.sliding_window = SlidingWindowManager(clock=clock, window_size=1.0)
        self.last_multiplicative_decrease: int = 0
        self.slow_start = True
        self.window_sizes = []

    def set_window_size(self, new_window_size: float, old_window_size: float):
        if new_window_size < old_window_size:
            log.add_event(type="Shrinking Window", desc=f"Old: {old_window_size}, New: {new_window_size}")
        if old_window_size < new_window_size:
            log.add_event(type="Expanding Window", desc=f"Old: {old_window_size}, New: {new_window_size}")
        self.sliding_window.set_window_size(new_window_size) 

    @staticmethod
    def plot(window_sizes: List[int]):
        plt.plot(window_sizes, label="Window Sizes", color="red", linewidth=2, alpha=0.5)
        plt.ylabel("Window Size")
        plt.xlabel("Tick")
        plt.legend()
        plt.savefig("aimd-window-sizes.png")
        plt.close()

    def shutdown_hook(self):
        #  Save the window sizes over time so that, when the simulation finishes, we can plot them over time.
        #  Then, pass those values in here
        self.plot(self.window_sizes) 

    def advance_sequence_number(self) -> int:
        if self.last_transmitted_sequence_number is None:
            self.last_transmitted_sequence_number = 0
        else:
            self.last_transmitted_sequence_number += 1
        return self.last_transmitted_sequence_number

    def run_one_tick(self) -> int | None:
        current_time = self.clock.read_tick()
        # Every tick, we record the widow size, and we can plot it 
        self.window_sizes.append(self.sliding_window.get_window_size())

        # TODO: STEP 1 - Process newly received messages
        #  - These will all be acknowledgement to messages this host has previously sent out.
        #  - You should mark these messages as successfully delivered.
        #  - You should also increase the size of the window
        #      - You should start in "slow-start" mode to quickly ramp up to the bandwidth capacity.
        #      - Exit "slow-start" mode and enter congestion-avoidance mode once your first timeout occurs
        packets_received = self.network_interface.receive_all()
        for packet in packets_received:
            # Compute and record the RTT

            # Update inflight information for self.sliding_window
            self.sliding_window.remove_inflight_information(packet.sequence_number)

            # Update the window size
            new_window = 0 # TODO: Calculate the correct value for new_window
            # Hint: if it is in slow start mode, how should we update the window size?
            # If is in congestion avoidance mode, how should we update the window size?
            # Note that window size update is triggered by every acked packet, but in class we descibe
            # exponential/linear window size update based on every RTT. How to bridge them?
            # You may find the excerpt useful 
            # https://www.dropbox.com/scl/fi/lo8tviblxzugn8te3v8wg/book-excerpt.pdf?rlkey=xie2osifzgmox1vyxopz9h7sh&dl=0

            self.set_window_size(new_window, self.sliding_window.get_window_size())

        # TODO: STEP 2 - Retry any messages that have timed out
        #  - When you transmit each packet (in steps 2 and 3), you should track that message as inflight
        #  - Check to see if there are any inflight messages who's timeout has already passed
        #  - If you find a timed out message, create a new packet and transmit it
        #      - The new packet should have the same sequence number
        #      - You should set the packet's retransmission_flag to true
        #      - The sent time should be the current timestamp
        #      - Use the transmit() function of the network interface to send the packet
        #  - Shrink the sliding window
        #      - This should happen at most once per RTT
        #      - The window size should not go below 1
        # REPLACE pass with your code

        retriable_packets = self.sliding_window.get_packets_to_retry()
        for retriable_message in retriable_packets:
            self.slow_start = False
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
