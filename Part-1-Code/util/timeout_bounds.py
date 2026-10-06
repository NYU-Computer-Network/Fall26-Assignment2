from dataclasses import dataclass


@dataclass
class TimeoutBounds:
    min: float | None
    max: float | None
