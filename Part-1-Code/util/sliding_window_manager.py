import dataclasses
import math
from typing import List

from simulation.clock import Clock
from simulation import simulation_logger as log


@dataclasses.dataclass
class Transmission:
    sequence_number: int
    timeout: int


class SlidingWindowManager:

    def __init__(self, clock: Clock, window_size: float):
        self.clock = clock
        self.window_size = window_size
        self.inflight: List[Transmission] = []

    def get_window_size(self) -> float:
        return self.window_size

    def set_window_size(self, window_size: float):
        self.window_size = window_size

    def compute_number_of_packets_to_send(self) -> int:
        return max(math.floor(self.window_size) - len(self.inflight), 0)

    def get_packets_to_retry(self) -> List[Transmission]:
        current_time = self.clock.read_tick()
        return [packet for packet in self.inflight if packet.timeout < current_time]

    def get_largest_in_order_sequence_number(self) -> int | None:
        if len(self.inflight) == 0:
            return None
        earliest_unacknowledged_packet = self.inflight[0].sequence_number
        return None if earliest_unacknowledged_packet == 0 else earliest_unacknowledged_packet - 1

    def remove_inflight_information(self, seq_num: int):
        self.inflight = [unacked for unacked in self.inflight if unacked.sequence_number != seq_num]

    def add_inflight_information(self, seq_num: int, timeout: int):
        self.inflight.append(Transmission(seq_num, timeout))
