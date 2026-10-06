#!/usr/bin/env python3
import argparse
import matplotlib.pyplot as plt
from dataclasses import dataclass
from numpy import clip, random

from util.timeout_calculator import TimeoutCalculator


@dataclass
class SimulatedMessageTransmission:
    send_time: float
    rtt: float


@dataclass
class MessageTransmissionResult:
    # The timestamp for when this message was sent
    send_time: float

    # The RTT of this message and its ack
    packet_rtt: float

    # An estimate of the mean RTT of messages up to this point, computed using EWMA
    transmission_rtt_mean_estimate: float

    # An estimate of the stddiv of RTT for messages up to this point, computed using EWMA
    transmission_rtt_stddiv_estimate: float

    # The timeout that was set after this packet was processed
    timeout: float

    # Extra time that we would have waited beyond when the ack arrived.
    # If we knew the RTT of a packet in advance, we could retry as soon as the expected RTT elapsed.
    # So we can view the difference between time timeout and the RTT as "extra" wait time.
    extra_wait_time: float

    # Would the ack have been ignored?
    ack_ignored: bool


# Generate the RTT data for our simulation
class NetworkSimulator:
    @staticmethod
    def short_spike():
        for ts in range(0, 10):
            yield SimulatedMessageTransmission(send_time=ts, rtt=100)
        for ts in range(10, 12):
            yield SimulatedMessageTransmission(send_time=ts, rtt=200)
        for ts in range(12, 100):
            yield SimulatedMessageTransmission(send_time=ts, rtt=100)

    @staticmethod
    def long_spike():
        for ts in range(0, 10):
            yield SimulatedMessageTransmission(send_time=ts, rtt=100)
        for ts in range(10, 30):
            yield SimulatedMessageTransmission(send_time=ts, rtt=200)
        for ts in range(30, 100):
            yield SimulatedMessageTransmission(send_time=ts, rtt=100)

    @staticmethod
    def permanent_change():
        for ts in range(0, 20):
            yield SimulatedMessageTransmission(send_time=ts, rtt=100)
        for ts in range(20, 100):
            yield SimulatedMessageTransmission(send_time=ts, rtt=200)

    @staticmethod
    def high_variance():
        previous = 1.0
        for ts in range(0, 100):
            yield SimulatedMessageTransmission(send_time=ts, rtt=previous)
            diff = random.normal(loc=0, scale=25)
            previous = clip(previous + diff, 10, 200)


def run_simulation(network_simulator, alpha: float, beta: float, k: float) -> list:
    message_transmissions = []
    current_timeout = None
    timeout_calculator = TimeoutCalculator(alpha=alpha, beta=beta, k=k, initial_stddiv_estimate=0)

    for message in network_simulator():
        if current_timeout is None:
            current_timeout = message.rtt

        # First, let's see if this packet made it before the timeout we computed last time
        ack_ignored = message.rtt > current_timeout

        # If it wasn't ignored, see how long we would have waited unnecessarily, had the packet been dropped
        if ack_ignored:
            extra_wait_time = None
        else:
            extra_wait_time = message.rtt - current_timeout

        # Add the datapoint to the calculator
        timeout_calculator.add_data_point(message.rtt)

        # Record the results
        message_transmissions.append(
            MessageTransmissionResult(
                send_time=message.send_time,
                packet_rtt=message.rtt,
                transmission_rtt_mean_estimate=timeout_calculator.mean_estimate(),
                transmission_rtt_stddiv_estimate=timeout_calculator.stddiv_estimate(),
                timeout=current_timeout,
                extra_wait_time=extra_wait_time,
                ack_ignored=ack_ignored
            )
        )

        # Finally, update the timeout before the next message is sent
        current_timeout = timeout_calculator.timeout()

    return message_transmissions


def plot(message_transmissions: list):
    # First, extract the two data sets
    actual_rtt_data = list(map(lambda message: message.packet_rtt, message_transmissions))
    mean_estimates = list(map(lambda message: message.transmission_rtt_mean_estimate, message_transmissions))
    timeouts = list(map(lambda message: message.timeout, message_transmissions))

    # plot the distribution
    plt.plot(actual_rtt_data, label="RTT", color="red", linewidth=2, alpha=0.5)
    plt.plot(mean_estimates, label="Mean Estimate", color="blue", ls="dotted")
    plt.plot(timeouts, label="Timeout", color="green", ls="dotted")
    plt.legend()
    plt.savefig("timeout_simulation.png")


if __name__ == "__main__":
    arg_def = argparse.ArgumentParser(
        description="EWMA simulator. How do we determine when to timeout a message and retry?"
    )

    arg_def.add_argument(
        "simulation_scenario",
        choices=["short-spike", "long-spike", "high-variance", "permanent-change"],
        default="high-variance",
    )
    arg_def.add_argument(
        "-a", "--alpha",
        dest="alpha",
        type=float,
        required=True
    )
    arg_def.add_argument(
        "-b", "--beta",
        dest="beta",
        type=float,
        required=True
    )
    arg_def.add_argument(
        "-k", "--standard-deviations-for-timeout",
        dest="k",
        type=float,
        default=3
    )

    args = arg_def.parse_args()

    match args.simulation_scenario:
        case "short-spike":
            network_simulator = NetworkSimulator.short_spike
        case "long-spike":
            network_simulator = NetworkSimulator.long_spike
        case "high-variance":
            network_simulator = NetworkSimulator.high_variance
        case "permanent-change":
            network_simulator = NetworkSimulator.permanent_change

    random.seed(seed=1234)
    message_transmissions = run_simulation(network_simulator, args.alpha, args.beta, args.k)
    print(f"Alpha: {args.alpha}")
    print(f"Beta: {args.beta}")
    print(f"EWMA at step 35: {message_transmissions[35].transmission_rtt_mean_estimate}")
    print(f"EWMA at step 90: {message_transmissions[90].transmission_rtt_mean_estimate}")
    print()
    plot(message_transmissions)
