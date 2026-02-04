"""Random file system navigator."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

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
    files: set[FSEntry] = field(default_factory=set)
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

    def drop(self) -> FSEntry | None:
        """Drop a ball from the root."""
        current_path = self.root

        while True:
            pin = self.board[current_path]

            if pin.is_exhausted:
                return None

            if not pin.is_scanned:
                self.scan(pin)

            pin.files.difference_update(self.quota.locked_file)
            valid_files = pin.files
            valid_subdirs = [d for d in pin.subdirs if not (self.quota.is_dir_locked(d) or self.board[d].is_exhausted)]

            if not (valid_files or valid_subdirs):
                pin.is_exhausted = True
                self.quota.lock_dir(current_path)
                return None

            match bool(valid_subdirs), bool(valid_files):
                case True, True:
                    should_descend = self.rng.choice([True, False])
                case True, False:
                    should_descend = True
                case False, True:
                    should_descend = False
                case False, False:
                    should_descend = False

            if should_descend:
                next_dir = self.rng.choice(valid_subdirs)
                current_path = next_dir
                continue

            entry = valid_files.pop()
            self.quota.lock_file(entry)
            return entry

    def scan(self, pin: FSPachinkoPin) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        files = []
        try:
            with os.scandir(pin.path) as it:
                for e in it:
                    try:
                        if e.is_symlink() and not self.should_follow_symlink:
                            continue

                        if e.is_dir():
                            dirpath = e.path
                            pin.subdirs.append(dirpath)
                            if dirpath not in self.board:
                                self.board[dirpath] = FSPachinkoPin(path=dirpath)

                        elif e.is_file():
                            fsentry = FSEntry.from_direntry(e)
                            if self.validator.is_valid(fsentry):
                                files.append(fsentry)
                    except OSError:
                        continue
        except OSError:
            pin.is_exhausted = True

        self.rng.shuffle(pin.subdirs)
        self.rng.shuffle(files)
        pin.files = set(files)
        pin.is_scanned = True
