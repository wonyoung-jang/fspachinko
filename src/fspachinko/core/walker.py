"""Random file system navigator."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os import scandir
from os.path import splitext
from random import choice
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .quota import DiversityQuota
    from .validator import FileValidator

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class FSEntry:
    """Lightweight wrapper for os.DirEntry with only path and name."""

    path: str
    stem: str
    ext: str
    size: int

    @classmethod
    def from_direntry(cls, e: os.DirEntry) -> FSEntry:
        """Create a lightweight FSEntry from an os.DirEntry."""
        stem, ext = splitext(e.name)
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
    subdirs: tuple[str, ...] = field(default_factory=tuple)
    files: tuple[os.DirEntry, ...] = field(default_factory=tuple)
    is_scanned: bool = False
    is_exhausted: bool = False

    def scan(self, *, should_follow_symlink: bool) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        subdirs = []
        files = []
        try:
            with scandir(self.path) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=should_follow_symlink):
                            subdirs.append(e.path)
                        elif e.is_file(follow_symlinks=should_follow_symlink):
                            files.append(e)
                    except OSError:
                        continue
        except OSError:
            self.is_exhausted = True
            return

        self.subdirs = tuple(subdirs)
        self.files = tuple(files)
        self.is_scanned = True


@dataclass(slots=True)
class FSWalker(ABC):
    """Abstract file system walker."""

    @abstractmethod
    def walk(self) -> Iterator[os.DirEntry]:
        """Generate candidates for a given directory."""


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
        self.board[self.root] = FSPachinkoPin(path=self.root)

    def walk(self) -> Iterator[os.DirEntry]:
        """Continuously drop balls until the board is empty."""
        root = self.root
        curr = self.root
        board = self.board
        board_setdefault = board.setdefault
        board_pop = board.pop
        quota = self.quota
        is_dir_locked = quota.is_dir_locked
        is_file_locked = quota.is_file_locked
        lock_dir = quota.lock_dir
        lock_file = quota.lock_file

        while not board[root].is_exhausted:
            pin = board_setdefault(curr, FSPachinkoPin(path=curr))

            if not pin.is_scanned:
                pin.scan(should_follow_symlink=self.should_follow_symlink)

            subdirs = []
            for d in pin.subdirs:
                if is_dir_locked(d):
                    board_pop(d, None)
                else:
                    subdirs.append(d)

            pin.subdirs = tuple(subdirs)
            pin.files = tuple(f for f in pin.files if not is_file_locked(f))
            has_subdirs, has_files = bool(pin.subdirs), bool(pin.files)

            if not (has_subdirs or has_files):
                pin.is_exhausted = True
                lock_dir(curr)
                board_pop(curr, None)
                curr = root
                continue

            should_descend = choice((True, False)) if has_subdirs and has_files else has_subdirs
            if should_descend:
                curr = choice(pin.subdirs)
                continue

            entry = choice(pin.files)
            lock_file(entry)
            yield entry
            curr = root
