"""Mandala state dataclass."""

from dataclasses import dataclass
from time import perf_counter


@dataclass(slots=True)
class MandalaState:
    """Dataclass for Mandala state."""

    count: int = 0
    bytes_in_currdir: int = 0
    start_currdir: float = 0.0
    start_time: float = 0.0

    def reset_for_folder(self) -> None:
        """Reset state variables for a new folder."""
        self.count = 0
        self.bytes_in_currdir = 0
        _start = perf_counter()
        self.start_currdir = _start
        self.start_time = _start

    def update_success(self, size: int) -> None:
        """Update state on successful operation."""
        self.count += 1
        self.bytes_in_currdir += size
        self.start_time = perf_counter()
