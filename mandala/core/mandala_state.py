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
    touched_by_weight: dict[Path, bool] = field(default_factory=lambda: defaultdict(bool))
    weighted_counts: dict[Path, int] = field(default_factory=lambda: defaultdict(int))
    path_cache: dict[Path, list[Path]] = field(default_factory=lambda: defaultdict(list))
    count: int = 0
    bytes_in_current_folder: int = 0
    start_folder_time: float = 0.0
    start_stall_time: float = 0.0
    is_append_log: bool = False

    def reset_for_folder(self, root_absolute: Path, *, unique_folders: bool) -> None:
        """Reset state variables for a new folder."""
        self.count = 0
        self.bytes_in_current_folder = 0
        _start = perf_counter()
        self.start_folder_time = _start
        self.start_stall_time = _start
        self.weighted_counts.clear()
        self.touched_by_weight.clear()

        if unique_folders:
            self.touched_folders[root_absolute] = False
            for key in self.touched_by_weight:
                self.touched_files[key] = False
                self.touched_folders[key] = False
        else:
            self.touched_files.clear()
            self.touched_folders.clear()
            self.path_cache.clear()

    def is_touched(self, abs_path: Path) -> bool:
        """Check if a file/folder is touched based on weight."""
        return self.touched_files[abs_path] or self.touched_folders[abs_path]

    def touch_folder_if_all_files_touched(self, abs_path: Path) -> None:
        """Mark folder as touched if all files inside are touched."""
        for file_folder in self.path_cache[abs_path]:
            p = file_folder.resolve()
            if not (self.touched_files[p] or self.touched_folders[p]):
                return

        self.touched_folders[abs_path] = True

    def update_success(self, size: int) -> None:
        """Update state on successful operation."""
        self.count += 1
        self.bytes_in_current_folder += size
        self.start_stall_time = perf_counter()

    def handle_weight(self, mark: Path, weight: int) -> None:
        """Handle weight-based touching of folders."""
        if weight <= 0:
            return

        self.weighted_counts[mark] += 1
        if self.weighted_counts[mark] == weight:
            self.touched_folders[mark] = True
            self.touched_by_weight[mark] = True
