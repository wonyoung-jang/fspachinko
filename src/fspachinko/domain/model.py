"""Model classes for the domain."""

from collections import Counter, deque
from dataclasses import dataclass, field

from .events import DirectoryStarted, DirectoryTransferred, Event, FileTransferred


@dataclass(slots=True)
class DestinationDirectory:
    """Aggregate: Represents a destination directory for file transfer."""

    path: str
    target_qty: int
    files: dict[str, int] = field(default_factory=dict)  # Path: Size

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
    def size(self) -> int:
        """Get the total size of files in the directory."""
        return sum(self.files.values())

    def accept(self, size: int, path: str) -> None:
        """Update the directory stats after accepting a file."""
        self.files[path] = size


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
class TransferJob:
    """The Root Aggregate for a file transfer process."""

    quota: DiversityQuota = field(default_factory=DiversityQuota)
    is_stop_requested: bool = False
    dest_dir_inputs: list[tuple[str, int]] = field(default_factory=list)
    events: deque[Event] = field(default_factory=deque)

    @property
    def is_root_locked(self) -> bool:
        """Check if the root directory is locked."""
        return self.quota.is_root_locked

    def reset(self) -> None:
        """Reset the job state for a new transfer process."""
        self.quota.reset()

    def process_file(self, entry: FSEntry) -> bool:
        """Process a file transfer, checking the diversity quota and updating the destination directory stats."""
        return self.quota.can_accept(entry.parent, entry.path)

    def start_directory(self, dst: DestinationDirectory) -> None:
        """Update the directory count in the diversity quota after processing a file."""
        self.events.append(DirectoryStarted(path=dst.path, target_qty=dst.target_qty))

    def update_file(self, dst: DestinationDirectory, entry: FSEntry, new_path: str) -> None:
        """Update the job state after processing a file."""
        dst.accept(entry.size, new_path)
        self.quota.update(entry.parent, entry.path)
        self.events.append(FileTransferred(dst.count, entry.path, new_path))

    def request_stop(self) -> None:
        """Request to stop the process."""
        self.is_stop_requested = True

    def finalize_directory(self, dst: DestinationDirectory, *, is_empty_creation: bool) -> None:
        """Finalize the processing of a directory (e.g., for cleanup or reporting)."""
        self.events.append(
            DirectoryTransferred(
                path=dst.path,
                size=dst.size,
                count=dst.count,
                target_qty=dst.target_qty,
                is_success=dst.is_success,
                is_empty_creation=is_empty_creation,
                is_stop_requested=self.is_stop_requested,
                is_root_locked=self.is_root_locked,
            )
        )


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
    subdirs: list[str] = field(default_factory=list)
    files: list[FSEntry] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """Check if the pin has no subdirectories or files."""
        return not self.subdirs and not self.files

    @property
    def total_entries(self) -> int:
        """Get the total number of entries (subdirectories + files) in the pin."""
        return len(self.subdirs) + len(self.files)

    @property
    def subdir_total_ratio(self) -> float:
        """Get the ratio of subdirectories to total entries."""
        total = self.total_entries
        return len(self.subdirs) / total if total > 0 else 0.0
