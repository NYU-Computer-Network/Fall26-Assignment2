#!/usr/bin/env python3
import argparse
import random

from network.network_interface import NetworkInterface
from simulation import simulation_logger as log
from simulation.clock import Clock
from simulation.simulatorv2 import SimulatorV2 as Simulator
from util.timeout_bounds import TimeoutBounds
from util.timeout_calculator import TimeoutCalculator
from host.stop_and_wait_host import StopAndWaitHost
from host.sliding_window_host import SlidingWindowHost
from host.aimd_host import AimdHost


def rtt_type(arg: str):
    try:
        rtt = float(arg)
    except ValueError:    
        raise argparse.ArgumentTypeError("RTT minimum must be a floating point number")
    if rtt < 2:
        raise argparse.ArgumentTypeError("RTT minimum must be at least 2")
    return rtt


if __name__ == "__main__":
    # Top level arguments. This is where we will determine the host type and allow users to pass in "global" arguments
    arg_def = argparse.ArgumentParser(
        description="Assignment 2 simulator. Link capacity is always 1 packet per tick"
    )
    arg_sub_parsers = arg_def.add_subparsers(dest='host_type')
    # Required global arguments
    arg_def.add_argument(
        "--rtt-min",
        dest="rtt_min",
        type=int,
        help="Minimum round-trip time in tick units",
        required=True,
    )
    arg_def.add_argument(
        "--ticks",
        dest="ticks",
        type=int,
        help="Number of ticks to run simulation for",
        required=True,
    )
    # optional arguments
    arg_def.add_argument(
        "--seed",
        dest="seed",
        type=int,
        help="a seed for the psuedo-randomness sim generator, defaults to a random value",
        default=random.randint(1, 99999)
    )
    arg_def.add_argument(
        "--loss-ratio",
        dest="loss_ratio",
        type=float,
        help="independent and identically distributed loss probability, default 0",
        default=0.0,
    )
    arg_def.add_argument(
        "--queue-limit",
        dest="queue_limit",
        type=int,
        help="max. queue size of link queue, defaults to 1M packets, which is practically infinite",
        default=1000000,
    )
    arg_def.add_argument(
        "--min-timeout",
        dest="min_timeout",
        type=int,
        default=TimeoutCalculator.DEFAULT_MIN_TIMEOUT,
        help="The minimum timeout value possible for the TimeoutCalculator",
    )
    arg_def.add_argument(
        "--max-timeout",
        dest="max_timeout",
        type=int,
        default=TimeoutCalculator.DEFAULT_MAX_TIMEOUT,
        help="The maximum timeout value possible for the TimeoutCalculator",
    )

    # Create subparser for "Stop and Wait" host type
    stop_and_wait_args = arg_sub_parsers.add_parser("stop-and-wait", help="Create a simulation with a host implementing the \"stop and wait\" protocol")

    # Create subparser for "Sliding Window" host type
    sliding_window_args = arg_sub_parsers.add_parser("sliding-window", help="Create a simulation with a host implementing the \"sliding window\" protocol")
    sliding_window_args.add_argument(
        "--window-size",
        dest="window_size",
        type=int,
        help="Window size in packets for sliding window sender",
        required=True
    )

    # Create subparser for "AIMD" host type
    aimd_args = arg_sub_parsers.add_parser("aimd", help="Create a simulation with a host implementing the \"AIMD\" protocol")

    # Actually carry out parsing
    args = arg_def.parse_args()
    for arg in vars(args):
        print("%s: %s" % (arg, getattr(args, arg)))

    clock = Clock()
    network_interface = NetworkInterface(clock)
    timeout_bounds = TimeoutBounds(args.min_timeout, args.max_timeout)
    timeout_calculator = TimeoutCalculator(
        alpha=0.125,
        beta=0.25,
        k=4.0,
        bounds=timeout_bounds
    )

    # Create the host based on the host_type, i.e., what protocol the host follows
    if args.host_type == "stop-and-wait":
        host = StopAndWaitHost(clock=clock, network_interface=network_interface, timeout_calculator=timeout_calculator)
    elif args.host_type == "sliding-window":
        host = SlidingWindowHost(clock=clock, network_interface=network_interface, timeout_calculator=timeout_calculator, window_size=args.window_size)
    elif args.host_type == "aimd":
        host = AimdHost(clock=clock, network_interface=network_interface, timeout_calculator=timeout_calculator)
    else:
        assert False

    # Start and run the simulation
    random.seed(args.seed)
    simulator = Simulator(
        host=host,
        clock=clock,
        network_interface=network_interface,
        loss_ratio=args.loss_ratio,
        queue_limit=args.queue_limit,
        rtt_min=args.rtt_min,
    )

    log.set_clock(clock)
    simulator.run(duration=args.ticks)
    log.print_logs()

    # Report the largest sequence number that has been received in order
    print(f"Maximum in order received sequence number {simulator.max_in_order_received_sequence_number()}")
