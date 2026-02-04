"""Random file system navigator."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from line_profiler import profile

if TYPE_CHECKING:
    from collections.abc import Iterator
    from random import Random

    from .quota import DiversityQuota
    from .validator import FileValidator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FSWalker(ABC):
    """Abstract file system walker."""

    @abstractmethod
    def walk(self) -> Iterator[FSEntry]:
        """Generate candidates for a given directory."""


@dataclass(slots=True)
class FSEntry:
    """Lightweight wrapper for os.DirEntry with only path and name."""

    path: str
    stem: str
    ext: str
    size: int

    @classmethod
    def from_direntry(cls, e: os.DirEntry) -> FSEntry:
        """Create a lightweight FSEntry from an os.DirEntry."""
        stem, ext = os.path.splitext(e.name)
        return cls(
            path=e.path,
            stem=stem,
            ext=ext,
            size=e.stat().st_size,
        )

    def __hash__(self) -> int:
        """Return the hash based on the file path."""
        return hash(self.path)

    def __fspath__(self) -> str:
        """Return the file system path representation."""
        return self.path


@dataclass(slots=True)
class FSPachinkoPin:
    """Represents a 'pin' on the Pachinko board."""

    path: str
    subdirs: list[str] = field(default_factory=list)
    files: list[FSEntry] = field(default_factory=list)
    is_scanned: bool = False
    is_exhausted: bool = False


@dataclass(slots=True)
class PachinkoFSWalker(FSWalker):
    """Simulates a Pachinko machine.

    For every file needed, we 'drop' a search cursor from the Root.
    It bounces randomly down directory paths until it settles on a file.
    """

    root: str
    quota: DiversityQuota
    validator: FileValidator
    rng: Random
    should_follow_symlink: bool
    board: dict[str, FSPachinkoPin] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize the board with the root pin."""
        self.board[self.root] = FSPachinkoPin(path=self.root)

    def walk(self) -> Iterator[FSEntry]:
        """Continuously drop balls until the board is empty."""
        while True:
            if self.board[self.root].is_exhausted:
                return

            if entry := self.drop():
                yield entry
            else:
                if self.board[self.root].is_exhausted:
                    return
                continue

    @profile
    def drop(self) -> FSEntry | None:
        """Drop a ball from the root."""
        current_path = self.root
        while True:
            pin = self.board[current_path]
            if pin.is_exhausted:
                return None

            if not pin.is_scanned:
                self.scan(pin)

            valid_subdirs = self.get_valid_subdirs(pin)
            valid_files = pin.files

            if not valid_subdirs and not valid_files:
                self.mark_exhausted(pin)
                return None

            if self.should_descend(valid_subdirs, valid_files):
                current_path = self.rng.choice(valid_subdirs)
                continue

            entry = pin.files.pop()
            self.quota.lock_file(entry)
            return entry

    def get_valid_subdirs(self, pin: FSPachinkoPin) -> list[str]:
        """Get valid subdirectories for a given pin."""
        set_subdirs = set(pin.subdirs).difference(self.quota.locked_dir)
        valid = [d for d in set_subdirs if not self.board[d].is_exhausted]
        pin.subdirs = valid
        return valid

    def mark_exhausted(self, pin: FSPachinkoPin) -> None:
        """Mark a pin and all its subdirs as exhausted."""
        currpath = pin.path
        pin.is_exhausted = True
        self.quota.lock_dir(currpath)

    def should_descend(self, valid_subdirs: list[str], valid_files: list[FSEntry]) -> bool:
        """Decide whether to descend into a subdir or select a file."""
        has_subdirs = bool(valid_subdirs)
        has_files = bool(valid_files)
        if has_subdirs and has_files:
            return self.rng.choice([True, False])
        return has_subdirs

    def scan(self, pin: FSPachinkoPin) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        is_valid = self.validator.is_valid
        subdirs = []
        files = []
        try:
            with os.scandir(pin.path) as it:
                for e in it:
                    try:
                        if e.is_symlink() and not self.should_follow_symlink:
                            continue

                        if e.is_dir():
                            dirpath = e.path
                            subdirs.append(dirpath)
                            if dirpath not in self.board:
                                self.board[dirpath] = FSPachinkoPin(path=dirpath)

                        elif e.is_file():
                            fsentry = FSEntry.from_direntry(e)
                            if is_valid(fsentry):
                                files.append(fsentry)
                    except OSError:
                        continue
        except OSError:
            pin.is_exhausted = True
            return

        if subdirs:
            self.rng.shuffle(subdirs)
        if files:
            self.rng.shuffle(files)

        pin.subdirs = subdirs
        pin.files = files
        pin.is_scanned = True
