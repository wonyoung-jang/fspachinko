"""Random file system navigator."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field
from os import scandir
from os.path import basename, dirname, splitext
from random import choice
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .context import DiversityQuota

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FSEntry:
    """Lightweight wrapper for os.DirEntry."""

    path: str = field(init=False)
    stem: str = field(init=False)
    ext: str = field(init=False)
    size: int = field(init=False)
    entry: InitVar[os.DirEntry]
    follow_symlink: InitVar[bool]

    def __post_init__(self, entry: os.DirEntry, follow_symlink: bool) -> None:
        """Create a lightweight FSEntry from an os.DirEntry."""
        self.path = entry.path
        self.stem, self.ext = splitext(entry.name)
        self.size = entry.stat(follow_symlinks=follow_symlink).st_size

    def __fspath__(self) -> str:
        """Return the file system path representation."""
        return self.path

    @property
    def parent(self) -> str:
        """Return the parent directory name."""
        return basename(dirname(self.path))


@dataclass(slots=True)
class FSPachinkoPin:
    """Represents a 'pin' on the Pachinko board."""

    path: str
    subdirs: list[str] = field(default_factory=list)
    files: list[os.DirEntry] = field(default_factory=list)
    is_scanned: bool = False
    is_exhausted: bool = False

    def scan(self, *, follow: bool) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        self.is_scanned = True
        subdirs_append = self.subdirs.append
        files_append = self.files.append
        try:
            with scandir(self.path) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=follow):
                            subdirs_append(e.path)
                        elif e.is_file(follow_symlinks=follow):
                            files_append(e)
                    except OSError:
                        continue
        except OSError:
            self.is_exhausted = True


@dataclass(slots=True)
class FSWalker(ABC):
    """Abstract file system walker."""

    @abstractmethod
    def walk(self) -> Iterator[FSEntry]:
        """Generate candidates for a given directory."""


@dataclass(slots=True)
class PachinkoFSWalker(FSWalker):
    """Simulates a Pachinko machine.

    For every file needed, we 'drop' a search cursor from the Root.
    It bounces randomly down directory paths until it settles on a file.
    """

    root: str
    quota: DiversityQuota
    should_follow_symlink: bool
    board: dict[str, FSPachinkoPin] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize the board with the root pin."""
        self.board[self.root] = FSPachinkoPin(path=self.root)

    def walk(self) -> Iterator[FSEntry]:
        """Continuously drop balls until the board is empty."""
        root = self.root
        curr = self.root
        board = self.board
        board_setdefault = board.setdefault
        board_pop = board.pop
        quota = self.quota
        locked_dir, locked_file = quota.locked_dir, quota.locked_file
        lock_dir, lock_file = locked_dir.add, locked_file.add
        follow = self.should_follow_symlink

        while root in board:
            pin = board_setdefault(curr, FSPachinkoPin(path=curr))
            if not pin.is_scanned:
                pin.scan(follow=follow)

            pin.subdirs = subdirs = [d for d in pin.subdirs if d not in locked_dir]
            pin.files = files = [f for f in pin.files if f.path not in locked_file]

            if not (subdirs or files):
                pin.is_exhausted = True
                lock_dir(curr)
                board_pop(curr, None)
                if curr == root:
                    break
                curr = root
                continue

            should_descend = choice((True, False)) if subdirs and files else bool(subdirs)
            if should_descend:
                curr = choice(subdirs)
                continue

            entry = choice(files)
            lock_file(entry.path)
            fsentry = FSEntry(entry=entry, follow_symlink=follow)
            yield fsentry
            curr = root
