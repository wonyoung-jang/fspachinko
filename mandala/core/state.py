"""Mandala state dataclass."""

from dataclasses import dataclass
from time import perf_counter


@dataclass(slots=True)
class MandalaState:
    """Dataclass for Mandala state."""

    count: int = 0
    bytes_in_current_folder: int = 0
    start_folder_time: float = 0.0
    start_stall_time: float = 0.0
    is_append_log: bool = False

    def reset_for_folder(self) -> None:
        """Reset state variables for a new folder."""
        self.count = 0
        self.bytes_in_current_folder = 0
        _start = perf_counter()
        self.start_folder_time = _start
        self.start_stall_time = _start

    def update_success(self, size: int) -> None:
        """Update state on successful operation."""
        self.count += 1
        self.bytes_in_current_folder += size
        self.start_stall_time = perf_counter()
