"""Random file system navigator."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os import scandir
from os.path import basename, dirname, splitext
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
    parent: str
    stem: str
    ext: str
    size: int

    @classmethod
    def from_direntry(cls, e: os.DirEntry) -> FSEntry:
        """Create a lightweight FSEntry from an os.DirEntry."""
        path = e.path
        stem, ext = splitext(e.name)
        parent = basename(dirname(path))
        return cls(
            path=path,
            parent=parent,
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
    subdirs: tuple[str, ...] = ()
    files: tuple[os.DirEntry, ...] = ()
    is_scanned: bool = False
    is_exhausted: bool = False

    def scan(self, *, follow: bool) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        subdirs = []
        files = []
        try:
            with scandir(self.path) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=follow):
                            subdirs.append(e.path)
                        elif e.is_file(follow_symlinks=follow):
                            files.append(e)
                    except OSError:
                        logger.debug("Skipping entry due to OSError: %s", e.path)
                        continue
        except OSError:
            self.is_exhausted = True
            logger.debug("Skipping pin scan due to OSError: %s", self.path)
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
        locked_dir = quota.locked_dir
        locked_file = quota.locked_file
        lock_dir = locked_dir.add
        lock_file = locked_file.add

        while not board[root].is_exhausted:
            pin = board_setdefault(curr, FSPachinkoPin(path=curr))

            if not pin.is_scanned:
                pin.scan(follow=self.should_follow_symlink)

            subdirs = []
            for d in pin.subdirs:
                if d in locked_dir:
                    board_pop(d, None)
                else:
                    subdirs.append(d)

            pin.subdirs = tuple(subdirs)
            pin.files = tuple(f for f in pin.files if f not in locked_file)
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
