"""Model classes for the domain."""

from collections import Counter
from dataclasses import dataclass, field

from fspachinko.domain.commands import Command
from fspachinko.domain.events import Event

type Message = Command | Event


@dataclass(slots=True)
class DiversityQuota:
    """Represents the diversity quota for the process.

    This is a "global" object that tracks across multiple directories.
    It has no real "identifier", so it is not an entity.
    It is not really a value object either.
    It is purely a rule enforcer.

    There are two main rules:
    1. If the max_per_dir is set, then no more than that number of files can be accepted from the same parent directory.
        - For example, if max_per_dir is 2, then a dest can have at most 2 files from parent A.
    2. If unique_files_only is set, then no file can be accepted more than once across the entire process.
        - Otherwise, dest 1 may have file A and dest 2 may also have file A.

    There is also an implicit special rule for the root:
        - If the root is locked because max_per_dir is set, then no more files can be accepted.
        - Root locking = process is stopped.
    """

    root: str = ""
    max_per_dir: int | float = 0
    unique_files_only: bool = False
    files: set[str] = field(default_factory=set)
    directories: Counter[str] = field(default_factory=Counter)

    @property
    def is_root_locked(self) -> bool:
        """Check if the root directory is locked."""
        return self.directories[self.root] >= self.max_per_dir

    def reset(self) -> None:
        """Reset the locked file and directory sets."""
        self.directories.clear()
        if not self.unique_files_only:
            self.files.clear()

    def can_accept(self, parent: str, path: str) -> bool:
        """Check if a file can be accepted based on the diversity quota."""
        if path in self.files:
            return False
        return not self.directories[parent] >= self.max_per_dir

    def update(self, parent: str, path: str) -> None:
        """Update the locked directory count after accepting a file."""
        self.files.add(path)
        self.directories[parent] += 1


@dataclass(slots=True)
class DestinationDirectory:
    """Aggregate: Represents a destination directory for file transfer."""

    path: str
    target_qty: int
    should_create: bool
    size: int = 0
    files: set[str] = field(default_factory=set, init=False, repr=False)

    @property
    def count(self) -> int:
        """Get the current count of files in the directory."""
        return len(self.files)

    @property
    def is_success(self) -> bool:
        """Check if the directory has reached its target quantity."""
        return self.count >= self.target_qty

    @property
    def is_none_found(self) -> bool:
        """Check if no valid files were found."""
        return self.count == 0

    @property
    def is_empty_creation(self) -> bool:
        """Check if the directory was created but no files were found."""
        return self.should_create and self.is_none_found

    def add(self, path: str, size: int) -> None:
        """Update the directory stats after accepting a file."""
        self.files.add(path)
        self.size += size


@dataclass(slots=True)
class TransferJob:
    """The Root Aggregate for a file transfer process."""

    quota: DiversityQuota = field(default_factory=DiversityQuota)
    is_stop_requested: bool = False

    @property
    def is_stop_condition(self) -> bool:
        """Check if any stop condition is met (either stop requested or root locked)."""
        return self.is_stop_requested or self.is_root_locked

    @property
    def is_root_locked(self) -> bool:
        """Check if the root directory is locked."""
        return self.quota.is_root_locked

    def can_accept(self, entry: FSEntry) -> bool:
        """Check if a file can be accepted based on the diversity quota."""
        return self.quota.can_accept(entry.parent, entry.path)

    def request_stop(self) -> None:
        """Request to stop the process."""
        self.is_stop_requested = True

    def start_directory(self) -> None:
        """Update the directory count in the diversity quota after processing a file."""
        self.quota.reset()

    def register_transfer(self, dst: DestinationDirectory, entry: FSEntry, newpath: str) -> None:
        """Update the job state after processing a file."""
        dst.add(newpath, entry.size)
        self.quota.update(entry.parent, entry.path)


@dataclass(slots=True, frozen=True)
class FSEntry:
    """Value object wrapper for os.DirEntry.

    The identifires are:
    1. The path attribute
    2. All attributes

    os.DirEntry objects are lightweight, but FSEntry is slightly lighter
    and more convenient for our use case. Since the process potentially stores
    many of file entries, this tradeoff is worth it.
    """

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
    subdirs: list[str] = field(default_factory=list, init=False, repr=False)
    files: list[FSEntry] = field(default_factory=list, init=False, repr=False)

    def __len__(self) -> int:
        """Get the total number of entries (subdirectories + files) in the pin."""
        return len(self.subdirs) + len(self.files)

    @property
    def is_empty(self) -> bool:
        """Check if the pin has no subdirectories or files."""
        return len(self) == 0

    @property
    def subdir_total_ratio(self) -> float:
        """Get the ratio of subdirectories to total entries."""
        total = len(self)
        return len(self.subdirs) / total if total else 0.0
