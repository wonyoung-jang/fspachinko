"""Random file system navigator."""

import os
from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field
from os import scandir
from os.path import basename, dirname, splitext
from random import choice
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


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

    path: InitVar[str]
    follow: InitVar[bool]
    subdirs: list[str] = field(default_factory=list)
    files: list[os.DirEntry] = field(default_factory=list)

    def __post_init__(self, path: str, follow: bool) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        try:
            with scandir(path) as it:
                subdirs_append = self.subdirs.append
                files_append = self.files.append
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=follow):
                            subdirs_append(e.path)
                        elif e.is_file(follow_symlinks=follow):
                            files_append(e)
                    except OSError:
                        continue
        except OSError:
            return


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
    should_follow_symlink: bool
    board: dict[str, FSPachinkoPin] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize the board with the root pin."""
        self.board[self.root] = FSPachinkoPin(self.root, self.should_follow_symlink)

    def walk(self) -> Iterator[FSEntry]:
        """Iterate through FSEntry objects."""
        root = self.root
        curr = self.root
        board_setdefault, board_pop = self.board.setdefault, self.board.pop
        follow = self.should_follow_symlink

        while root in self.board:
            pin = board_setdefault(curr, FSPachinkoPin(curr, follow))
            subdirs, files = pin.subdirs, pin.files

            if not (subdirs or files):
                board_pop(curr, None)
                if curr == root:
                    break

                curr = root
                continue

            should_descend = choice((True, False)) if subdirs and files else bool(subdirs)
            if should_descend:
                curr = choice(subdirs)
                continue

            if files:
                yield FSEntry(entry=choice(files), follow_symlink=follow)

            curr = root
