"""Random file system navigator."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from random import choice
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

    def scan(self, *, should_follow_symlink: bool) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        subdirs = self.subdirs
        files = self.files
        try:
            with os.scandir(self.path) as it:
                for e in it:
                    try:
                        if e.is_symlink() and not should_follow_symlink:
                            continue

                        if e.is_dir(follow_symlinks=should_follow_symlink):
                            subdirs.append(e.path)
                        elif e.is_file(follow_symlinks=should_follow_symlink):
                            files.append(e)
                    except OSError:
                        continue
        except OSError:
            self.is_exhausted = True
            return

        self.is_scanned = True


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

    @profile
    def walk(self) -> Iterator[os.DirEntry]:
        """Continuously drop balls until the board is empty."""
        curr = self.root

        while not self.board[self.root].is_exhausted:
            pin = self.board.setdefault(curr, FSPachinkoPin(path=curr))

            if not pin.is_scanned:
                pin.scan(should_follow_symlink=self.should_follow_symlink)

            subdirs = []
            for d in pin.subdirs:
                if self.quota.is_dir_locked(d):
                    self.board.pop(d, None)
                else:
                    subdirs.append(d)

            pin.subdirs = subdirs
            pin.files = [f for f in pin.files if not self.quota.is_file_locked(f)]
            has_subdirs, has_files = bool(pin.subdirs), bool(pin.files)

            if not (has_subdirs or has_files):
                pin.is_exhausted = True
                self.quota.lock_dir(curr)
                self.board.pop(curr, None)
                curr = self.root
                continue

            should_descend = choice((True, False)) if has_subdirs and has_files else has_subdirs

            if should_descend:
                curr = choice(pin.subdirs)
                continue

            entry = choice(pin.files)
            self.quota.lock_file(entry)
            yield entry
            curr = self.root
