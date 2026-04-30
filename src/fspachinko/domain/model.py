"""Model classes for the domain."""

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fspachinko.domain.commands import Command
from fspachinko.domain.events import Event

if TYPE_CHECKING:
    from collections.abc import Iterator

type Message = Command | Event


@dataclass(slots=True)
class DestinationDirectory:
    """Aggregate: Represents a destination directory for file transfer."""

    path: str
    target_qty: int
    should_create: bool
    size: int = 0
    _files: set[str] = field(default_factory=set, init=False)

    def __iter__(self) -> Iterator[str]:
        """Iterate over the file paths in the directory."""
        return iter(self._files)

    def __contains__(self, item: str) -> bool:
        """Check if a file path is already in the directory."""
        return item in self._files

    def __len__(self) -> int:
        """Get the number of files currently in the directory."""
        return len(self._files)

    @property
    def is_success(self) -> bool:
        """Check if the directory has reached its target quantity."""
        return len(self) >= self.target_qty

    @property
    def is_none_found(self) -> bool:
        """Check if no valid files were found."""
        return len(self) == 0

    @property
    def is_empty_creation(self) -> bool:
        """Check if the directory was created but no files were found."""
        return self.should_create and self.is_none_found

    def add(self, path: str, size: int) -> None:
        """Update the directory stats after accepting a file."""
        self._files.add(path)
        self.size += size


@dataclass(slots=True)
class TransferJob:
    """The Root Aggregate for a file transfer process."""

    root: str = ""
    max_per_dir: int | float = 0
    is_stop_requested: bool = False
    _directories: Counter[str] = field(default_factory=Counter)

    @property
    def is_stop_condition(self) -> bool:
        """Check if any stop condition is met (either stop requested or root locked)."""
        return self.is_stop_requested or self.is_root_locked

    @property
    def is_root_locked(self) -> bool:
        """Check if the root directory is locked."""
        return self._directories[self.root] >= self.max_per_dir

    def can_accept(self, entry: FSEntry) -> bool:
        """Check if a file can be accepted based on the diversity quota."""
        return not self._directories[entry.parent] >= self.max_per_dir

    def request_stop(self) -> None:
        """Set the stop request flag."""
        self.is_stop_requested = True

    def reset(self) -> None:
        """Reset the job state for a new directory."""
        self._directories.clear()

    def register_transfer(self, entry: FSEntry) -> None:
        """Update the job state after processing a file."""
        self._directories[entry.parent] += 1


@dataclass(slots=True)
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
    mtime: int
    duration: float = 0.0

    @property
    def as_dict(self) -> dict[str, str | int | float]:
        """Return the FSEntry attributes as a dictionary."""
        return {
            "path": self.path,
            "stem": self.stem,
            "ext": self.ext,
            "parent": self.parent,
            "size": self.size,
            "mtime": self.mtime,
            "duration": self.duration,
        }

    @property
    def id_key(self) -> dict[str, str | int]:
        """Return the identifying attributes as a dictionary."""
        return {
            "path": self.path,
            "size": self.size,
            "mtime": self.mtime,
        }


@dataclass(slots=True)
class FSPachinkoPin:
    """Represents a 'pin' on the Pachinko board."""

    path: str
    subdirs: list[str] = field(default_factory=list, init=False)
    files: list[FSEntry] = field(default_factory=list, init=False)

    def __len__(self) -> int:
        """Get the total number of entries (subdirectories + files) in the pin."""
        return len(self.subdirs) + len(self.files)

    @property
    def subdir_total_ratio(self) -> float:
        """Get the ratio of subdirectories to total entries."""
        total = len(self)
        return len(self.subdirs) / total if total else 0.0
