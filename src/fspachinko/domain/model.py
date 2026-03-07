"""Model classes for the domain."""

from collections import Counter
from dataclasses import dataclass, field
from time import perf_counter

from ..helpers import get_report


@dataclass(slots=True)
class DestinationDirectory:
    """Aggregate: Represents a destination directory for file transfer."""

    path: str
    target_qty: int
    count: int = 0
    size: int = 0
    start_time: float = field(default_factory=perf_counter)

    @property
    def is_success(self) -> bool:
        """Check if the directory has reached its target quantity."""
        return self.count >= self.target_qty

    @property
    def is_none_found(self) -> bool:
        """Check if no valid files were found."""
        return self.count == 0

    @property
    def report_str(self) -> str:
        """Get the report string."""
        return get_report(self.path, self.size, self.start_time, self.count, self.target_qty)

    def accept(self, e: FSEntry) -> None:
        """Update the directory stats after accepting a file."""
        self.count += 1
        self.size += e.size


@dataclass(slots=True)
class DiversityQuota:
    """Represents the diversity quota for the process."""

    root: str
    max_per_dir: int | float
    unique_files_only: bool
    locked_file: set[str] = field(default_factory=set)
    locked_dir: Counter[str] = field(default_factory=Counter)

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        if self.max_per_dir <= 0:
            self.max_per_dir = float("inf")

    @property
    def is_root_locked(self) -> bool:
        """Check if the root directory is locked."""
        return self.root in self.locked_dir and self.locked_dir[self.root] >= self.max_per_dir

    def reset(self) -> None:
        """Reset the locked file and directory sets."""
        self.locked_dir.clear()
        if not self.unique_files_only:
            self.locked_file.clear()

    def can_accept(self, e: FSEntry) -> bool:
        """Check if a file can be accepted based on the diversity quota."""
        if e.path in self.locked_file:
            return False
        return not self.locked_dir[e.parent] >= self.max_per_dir

    def update(self, e: FSEntry) -> None:
        """Update the locked directory count after accepting a file."""
        self.locked_file.add(e.path)
        self.locked_dir[e.parent] += 1


@dataclass(slots=True, frozen=True)
class FSEntry:
    """Value object wrapper for os.DirEntry."""

    path: str
    stem: str
    ext: str
    parent: str
    size: int
    mtime: float
    duration: float = 0.0


@dataclass(slots=True)
class FSPachinkoPin:
    """Represents a 'pin' on the Pachinko board."""

    path: str
    is_scanned: bool = False
    subdirs: list[str] = field(default_factory=list)
    files: list[FSEntry] = field(default_factory=list)
