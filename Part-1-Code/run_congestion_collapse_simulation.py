#!/usr/bin/env python3
import random

import matplotlib.pyplot as plt
from host.host import Host
from network.network_interface import NetworkInterface
from simulation.clock import Clock
from simulation.simulatorv2 import SimulatorV2 as Simulator
from host.sliding_window_host import SlidingWindowHost
from util.timeout_calculator import TimeoutCalculator
from simulation import simulation_logger as log


DURATION = 10000


def return_congested_simulator(host: Host, network_interface: NetworkInterface, clock: Clock):
    random.seed(1000)
    return Simulator(
        host=host,
        network_interface=network_interface,
        clock=clock,
        loss_ratio=0.0,
        queue_limit=1000000,
        rtt_min=0,  # TODO: You're allowed to modify the RTT
    )


def tick_and_get_seq_number(window):
    clock = Clock()
    network_interface = NetworkInterface(clock=clock)
    timeout_calculator = TimeoutCalculator(alpha=0.125, beta=0.25, k=4)
    host = SlidingWindowHost(
        clock=clock,
        network_interface=network_interface,
        window_size=window,
        timeout_calculator=timeout_calculator
    )
    simulator = return_congested_simulator(host=host, network_interface=network_interface, clock=clock)
    log.set_clock(clock)
    simulator.run(DURATION)

    # Return the largest sequence number that has been received in order
    print(f"Maximum in order received sequence number {simulator.max_in_order_received_sequence_number()}")
    return simulator.max_in_order_received_sequence_number()


def get_window_sizes():
    # TODO: Select a progression of window sizes, which show a congestion collapse curve.
    return []

def plot(window_sizes, sequence_numbers):
    throughput = list(map(lambda seq_num: seq_num / DURATION, sequence_numbers))

    fig, window_sizes_axis = plt.subplots()
    throughput_axis = window_sizes_axis.twinx()

    window_sizes_axis.set_ylabel("Window size (packets)", color="red")
    window_sizes_axis.plot(window_sizes, label="Window Sizes", color="red", linewidth=2, alpha=0.5)

    throughput_axis.set_ylabel("Throughput (packets / tick)", color="blue")
    throughput_axis.plot(throughput, label="Sequence Numbers", color="blue", ls="dotted")

    fig.tight_layout()
    plt.savefig("congestion_collapse.png")


if __name__ == "__main__":
    # TODO: Select a progression of window sizes, which show a congestion collapse curve.
    window_sizes = get_window_sizes()
    # Should have at least 10 entries.
    assert len(window_sizes) >= 10
    # Windows should be strictly increasing
    assert all(x <= y for x, y in zip(window_sizes, window_sizes[1:]))

    # TODO: For each window size, call tick_and_get_seq_number
    # TODO: Collect the results
    # TODO: Plot the results using the plot() function
