"""Model classes for the domain."""

from collections import Counter, deque
from dataclasses import dataclass, field

from .events import DirectoryTransferred, Event, FileTransferred


@dataclass(slots=True)
class TransferJob:
    """The Root Aggregate for a file transfer process."""

    quota: DiversityQuota
    is_stop_requested: bool = False
    dst: DestinationDirectory | None = None
    events: deque[Event] = field(default_factory=deque)

    @property
    def is_root_locked(self) -> bool:
        """Check if the root directory is locked."""
        return self.quota.is_root_locked

    def reset(self) -> None:
        """Reset the job state for a new transfer process."""
        self.dst = None
        self.quota.reset()

    def process_file(self, entry: FSEntry) -> bool:
        """Process a file transfer, checking the diversity quota and updating the destination directory stats."""
        return self.quota.can_accept(entry.parent, entry.path)

    def update(self, entry: FSEntry, new_path: str) -> None:
        """Update the job state after processing a directory."""
        if self.dst is None:
            return

        self.quota.update(entry.parent, entry.path)
        self.dst.accept(entry.size)
        self.events.append(FileTransferred(self.dst.count, entry.path, new_path))

    def request_stop(self) -> None:
        """Request to stop the process."""
        self.is_stop_requested = True

    def finalize_directory(self, *, is_empty_creation: bool) -> None:
        """Finalize the processing of a directory (e.g., for cleanup or reporting)."""
        if self.dst:
            self.events.append(
                DirectoryTransferred(
                    path=self.dst.path,
                    size=self.dst.size,
                    count=self.dst.count,
                    target_qty=self.dst.target_qty,
                    is_success=self.dst.is_success,
                    is_empty_creation=is_empty_creation,
                    is_stop_requested=self.is_stop_requested,
                    is_root_locked=self.is_root_locked,
                )
            )


@dataclass(slots=True)
class DestinationDirectory:
    """Aggregate: Represents a destination directory for file transfer."""

    path: str
    target_qty: int
    count: int = 0
    size: int = 0

    @property
    def is_success(self) -> bool:
        """Check if the directory has reached its target quantity."""
        return self.count >= self.target_qty

    @property
    def is_none_found(self) -> bool:
        """Check if no valid files were found."""
        return self.count == 0

    def accept(self, size: int) -> None:
        """Update the directory stats after accepting a file."""
        self.count += 1
        self.size += size


@dataclass(slots=True)
class DiversityQuota:
    """Represents the diversity quota for the process."""

    root: str
    max_per_dir: int | float
    unique_files_only: bool
    locked_file: set[str] = field(default_factory=set)
    locked_dir: Counter[str] = field(default_factory=Counter)

    @property
    def is_root_locked(self) -> bool:
        """Check if the root directory is locked."""
        return self.locked_dir[self.root] >= self.max_per_dir

    def reset(self) -> None:
        """Reset the locked file and directory sets."""
        self.locked_dir.clear()
        if not self.unique_files_only:
            self.locked_file.clear()

    def can_accept(self, parent: str, path: str) -> bool:
        """Check if a file can be accepted based on the diversity quota."""
        if path in self.locked_file:
            return False
        return not self.locked_dir[parent] >= self.max_per_dir

    def update(self, parent: str, path: str) -> None:
        """Update the locked directory count after accepting a file."""
        self.locked_file.add(path)
        self.locked_dir[parent] += 1


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
