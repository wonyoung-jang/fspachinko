"""Random file system navigator."""

import itertools
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os import scandir
from typing import TYPE_CHECKING, Any

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
    def walk(self) -> Iterator[os.DirEntry]:
        """Generate candidates for a given directory."""


@dataclass(slots=True)
class RandomFSWalker(FSWalker):
    """Navigates the file system randomly based on Quota rules."""

    root: str
    quota: DiversityQuota
    rng: Random
    should_follow_symlink: bool
    validator: FileValidator
    tree: dict[str, set[os.DirEntry]] = field(default_factory=dict)
    directories: tuple[str, ...] = ()
    dir_idx_cycle: Iterator[int] = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the walker by scanning the root directory."""
        logger.debug("Scanning root directory: %s", self.root)
        self._scan_root()
        logger.debug("Completed scanning root directory.")

    @profile
    def _scan_root(self) -> None:
        """Scan the root directory and return its entries."""
        is_valid = self.validator.is_valid
        shuffle = self.rng.shuffle
        for dirpath, _, filenames in walk_entries(self.root, follow_symlinks=self.should_follow_symlink):
            if not filenames:
                continue

            entries = [f for f in filenames if is_valid(f)]
            if entries:
                shuffle(entries)
                self.tree[dirpath] = set(entries)

        self.directories = tuple(self.tree.keys())
        valid_idx = list(range(len(self.directories)))
        shuffle(valid_idx)
        self.dir_idx_cycle = itertools.cycle(valid_idx)

    @profile
    def walk(self) -> Iterator[os.DirEntry]:
        """Generate shuffled candidates for a given directory."""
        if not self.directories:
            self.quota.lock_root()
            return

        n_directories = len(self.directories)
        n_locked = 0
        is_dir_locked = self.quota.is_dir_locked
        get_available = self.quota.get_available
        lock_file = self.quota.lock_file
        lock_dir = self.quota.lock_dir
        should_follow_symlink = self.should_follow_symlink
        directories = self.directories
        tree = self.tree

        for di in self.dir_idx_cycle:
            dirpath = directories[di]
            if is_dir_locked(dirpath):
                n_locked += 1
                if n_locked >= n_directories:
                    return
                continue
            n_locked = 0

            entries = tree[dirpath]
            available = get_available(entries)
            tree[dirpath] = available

            if not available:
                lock_dir(dirpath)
                continue

            for entry in available:
                lock_file(entry)
                if not should_follow_symlink and entry.is_symlink():
                    continue

                yield entry
                break


def walk_entries(
    top: str, *, on_error: Any = None, follow_symlinks: bool = False
) -> Iterator[tuple[str, tuple[os.DirEntry, ...], tuple[os.DirEntry, ...]]]:
    """Reimplement os.walk with topdown walk of DirEntry objects.

    Args:
        top: Root directory to start walking from.
        on_error: Optional error handler.
        follow_symlinks: Whether to follow symbolic links.

    Yields:
        A tuple of (current path, directories, non-directories).
        current path is a string, directories and non-directories are tuples of os.DirEntry objects.

    """
    stack: list[str] = [top]
    islink, join = os.path.islink, os.path.join

    while stack:
        top = stack.pop()
        dirs: list[os.DirEntry] = []
        nondirs: list[os.DirEntry] = []

        try:
            with scandir(top) as entries:
                for entry in entries:
                    try:
                        if follow_symlinks:
                            is_dir = entry.is_dir()
                        else:
                            is_dir = not entry.is_junction() and entry.is_dir(follow_symlinks=False)
                    except OSError:
                        is_dir = False
                    (dirs if is_dir else nondirs).append(entry)
        except OSError as error:
            if on_error is not None:
                on_error(error)
            continue

        yield top, tuple(dirs), tuple(nondirs)

        for dir_item in reversed(dirs):
            new_path = join(top, dir_item.name)
            if follow_symlinks or not islink(new_path):
                stack.append(new_path)
