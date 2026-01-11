"""Mandala state dataclass."""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter


@dataclass(slots=True)
class MandalaState:
    """Dataclass for Mandala state."""

    touched_files: dict[Path, bool] = field(default_factory=lambda: defaultdict(bool))
    touched_folders: dict[Path, bool] = field(default_factory=lambda: defaultdict(bool))
    weighted_counts: dict[Path, int] = field(default_factory=lambda: defaultdict(int))
    count: int = 0
    bytes_in_current_folder: int = 0
    start_folder_time: float = 0.0
    start_stall_time: float = 0.0
    is_append_log: bool = False

    def reset_for_folder(self, *, unique_folders: bool) -> None:
        """Reset state variables for a new folder."""
        self.count = 0
        self.bytes_in_current_folder = 0
        _start = perf_counter()
        self.start_folder_time = _start
        self.start_stall_time = _start
        self.weighted_counts.clear()
        self.touched_folders.clear()
        if not unique_folders:
            self.touched_files.clear()

    def is_touched(self, path: Path) -> bool:
        """Check if a file/folder is touched based on weight."""
        return self.touched_files[path] or self.touched_folders[path]

    def touch_file(self, file_path: Path) -> None:
        """Mark a file as touched."""
        self.touched_files[file_path] = True

    def touch_dir(self, dir_path: Path) -> None:
        """Mark a directory as touched."""
        self.touched_folders[dir_path] = True

    def update_success(self, size: int) -> None:
        """Update state on successful operation."""
        self.count += 1
        self.bytes_in_current_folder += size
        self.start_stall_time = perf_counter()

    def handle_weight(self, dir_path: Path, weight: int) -> None:
        """Handle weight-based touching of folders."""
        if weight <= 0:
            return

        self.weighted_counts[dir_path] += 1
        if self.weighted_counts[dir_path] == weight:
            self.touched_folders[dir_path] = True
