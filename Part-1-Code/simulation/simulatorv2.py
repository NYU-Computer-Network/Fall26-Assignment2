from host.host import Host
from network.link import Link
from network.network_interface import NetworkInterface
from simulation.clock import Clock
from simulation.delay_box import DelayBox

"""
Simulator
=========

This class manages the simulation.

On each tick, we do the following:
1. Update the clock
2. Run the host. The host reads from it's network card's buffer and writes new outbound packets
3. Flush packets from the network card to the link
4. Flush the link to the delay box
5. Flush the delay box to the network card ingress buffer
"""
class SimulatorV2:
    def __init__(
            self,
            host: Host,
            network_interface: NetworkInterface,
            clock: Clock,
            loss_ratio: float,
            queue_limit: int,
            rtt_min: int,
    ):
        self.network_interface = network_interface
        self.host = host
        self.delay_box = DelayBox(clock=clock, prop_delay=rtt_min - 1)
        self.link = Link(loss_ratio=loss_ratio, queue_limit=queue_limit)
        self.clock = clock
        self.max_usable_seq_num = 0

    def __run_tick(self):
        # First, run the host
        self.max_usable_seq_num = self.host.run_one_tick()

        # Move packets from host to link
        host_packets = self.network_interface.pull_packets_from_network_interface()
        self.link.enqueue(host_packets)

        # Move packets from link to delay box
        link_packets = self.link.dequeue()
        self.delay_box.enqueue(link_packets)

        # Move packets from delay box to host
        delay_box_packets = self.delay_box.dequeue()
        self.network_interface.push_packets_to_network_interface(delay_box_packets)

    def run(self, duration: int):
        
        for tick in range(0, duration):
            self.clock.set_tick(tick)
            self.__run_tick()
        self.host.shutdown_hook()

    def max_in_order_received_sequence_number(self):
        return self.max_usable_seq_num
