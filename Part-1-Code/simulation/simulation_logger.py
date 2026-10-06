from dataclasses import dataclass

from simulation.clock import Clock

_event_type_head: str = 'Event Type'
_ticks_head: str = 'Tick'
_event_description_head: str = 'Event Description'


@dataclass
class _ColSizes:
    ticks: int
    type: int
    desc: int


@dataclass
class _Row:
    tick: int
    type: str
    desc: str


_events = []
_clock: Clock | None = None


def add_event(desc: str = "", type: str = ""):
    _events.append(_Row(tick=_clock.read_tick(), type=type, desc=desc))


def set_clock(clock: Clock):
    global _clock
    _clock = clock


def _print_line(items: list):
    print(f"|{'|'.join(items)}|")


def _print_head(col_sizes: _ColSizes):
    _print_line([
        f" {_ticks_head.ljust(col_sizes.ticks)} ",
        f" {_event_type_head.ljust(col_sizes.type)} ",
        f" {_event_description_head.ljust(col_sizes.desc)} ",
    ])


def _print_seperator(col_sizes: _ColSizes):
    _print_line([
        "-" * (col_sizes.ticks + 2),
        "-" * (col_sizes.type + 2),
        "-" * (col_sizes.desc + 2)
    ])


def _print_row(col_sizes: _ColSizes, event_type: str, ticks: int, event_desc: str):
    _print_line([
        f" {str(ticks).rjust(col_sizes.ticks)} ",
        f" {event_type.rjust(col_sizes.type)} ",
        f" {event_desc.ljust(col_sizes.desc)} ",
    ])


def _print_edge(col_sizes: _ColSizes):
    print("-" * (col_sizes.type + col_sizes.ticks + col_sizes.desc + 10))


def print_logs():
    if not _events:
        print("\nNo events to log.\n")
        return

    col_sizes = _ColSizes(
        ticks=max(len(_ticks_head), len(str(_events[-1].tick))),
        type=max(len(_event_type_head), len(max(_events, key=lambda e: len(e.type)).type)),
        desc=max(len(_event_description_head), len(max(_events, key=lambda e: len(e.desc)).desc))
    )

    print()
    _print_edge(col_sizes)
    _print_head(col_sizes)
    _print_seperator(col_sizes)
    for event in _events:
        _print_row(col_sizes, event.type, event.tick, event.desc)
    _print_edge(col_sizes)
    print()


def clear():
    global _events
    _events = []
