"""Random file system navigator."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from random import choice, shuffle
from typing import TYPE_CHECKING

from line_profiler import profile

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .quota import DiversityQuota
    from .validator import FileValidator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FSWalker(ABC):
    """Abstract file system walker."""

    @abstractmethod
    def reset(self) -> None:
        """Reset the walker for a new batch."""

    @abstractmethod
    def walk(self) -> Iterator[os.DirEntry]:
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
    files: list[os.DirEntry] = field(default_factory=list)
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
    should_follow_symlink: bool
    board: dict[str, FSPachinkoPin] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize the board with the root pin."""
        self.reset()

    def reset(self) -> None:
        """Reset the walker and quota for a new batch."""
        self.board.clear()
        self.board[self.root] = FSPachinkoPin(path=self.root)

    def walk(self) -> Iterator[os.DirEntry]:
        """Continuously drop balls until the board is empty."""
        while not self.board[self.root].is_exhausted:
            if (entry := self.drop()) is not None:
                yield entry

    @profile
    def drop(self) -> os.DirEntry | None:
        """Drop a ball from the root."""
        current_path = self.root

        while True:
            pin = self.board[current_path]

            if pin.is_exhausted:
                return None

            if not pin.is_scanned:
                self.scan(pin)

            self.get_valid_subdirs(pin)

            has_subdirs, has_files = bool(pin.subdirs), bool(pin.files)
            is_exhausted = not (has_subdirs or has_files)

            if is_exhausted:
                self.mark_exhausted(pin)
                return None

            if self.should_descend(has_subdirs=has_subdirs, has_files=has_files):
                current_path = choice(pin.subdirs)
                continue

            return pin.files.pop()

    def get_valid_subdirs(self, pin: FSPachinkoPin) -> None:
        """Get valid subdirectories for a given pin."""
        pin.subdirs = [d for d in pin.subdirs if not self.quota.is_dir_locked(d) and not self.board[d].is_exhausted]

    def mark_exhausted(self, pin: FSPachinkoPin) -> None:
        """Mark a pin as exhausted."""
        currpath = pin.path
        pin.is_exhausted = True
        self.quota.lock_dir(currpath)

    def should_descend(self, *, has_subdirs: bool, has_files: bool) -> bool:
        """Decide whether to descend into a subdir or select a file."""
        if has_subdirs and has_files:
            return choice((True, False))
        return has_subdirs

    @profile
    def scan(self, pin: FSPachinkoPin) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        subdirs = []
        files = []
        should_follow_symlink = self.should_follow_symlink
        board = self.board

        try:
            with os.scandir(pin.path) as it:
                for e in it:
                    try:
                        if e.is_symlink() and not should_follow_symlink:
                            continue

                        if e.is_dir(follow_symlinks=should_follow_symlink):
                            dirpath = e.path
                            subdirs.append(dirpath)
                            board.setdefault(dirpath, FSPachinkoPin(path=dirpath))
                        elif e.is_file(follow_symlinks=should_follow_symlink):
                            files.append(e)
                    except OSError:
                        continue
        except OSError:
            pin.is_exhausted = True
            return

        if subdirs:
            shuffle(subdirs)
        if files:
            shuffle(files)

        pin.subdirs = subdirs
        pin.files = files
        pin.is_scanned = True
