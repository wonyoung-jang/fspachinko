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
    from .validator import FileValidator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FSEntry:
    """Lightweight wrapper for os.DirEntry with only path and name."""

    path: str = ""
    parent: str = ""
    stem: str = ""
    ext: str = ""
    size: int = 0
    entry: InitVar[os.DirEntry | None] = None
    follow_symlink: InitVar[bool] = False

    def __post_init__(self, entry: os.DirEntry, follow_symlink: bool) -> None:
        """Create a lightweight FSEntry from an os.DirEntry."""
        self.path = entry.path
        self.parent = basename(dirname(self.path))
        self.stem, self.ext = splitext(entry.name)
        self.size = entry.stat(follow_symlinks=follow_symlink).st_size

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
    validator: FileValidator
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

        while not board[root].is_exhausted:
            pin = board_setdefault(curr, FSPachinkoPin(path=curr))

            if not pin.is_scanned:
                self.scan(pin)

            subdirs = []
            for d in pin.subdirs:
                if d in locked_dir:
                    board_pop(d, None)
                else:
                    subdirs.append(d)

            pin.subdirs = subdirs
            pin.files = [f for f in pin.files if f.path not in locked_file]
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
            lock_file(entry.path)
            if self.validator.is_valid(entry):
                yield entry

            curr = root

    def scan(self, pin: FSPachinkoPin) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        follow = self.should_follow_symlink
        subdirs = pin.subdirs.append
        files = pin.files.append
        try:
            with scandir(pin.path) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=follow):
                            subdirs(e.path)
                        elif e.is_file(follow_symlinks=follow):
                            files(FSEntry(entry=e, follow_symlink=follow))
                    except OSError:
                        logger.debug("Skipping entry due to OSError: %s", e.path)
                        continue
        except OSError:
            pin.is_exhausted = True
            logger.debug("Skipping pin scan due to OSError: %s", pin.path)
            return

        pin.is_scanned = True
