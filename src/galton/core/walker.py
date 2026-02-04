"""Random file system navigator."""

import itertools
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from os import scandir
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from random import Random

    from .quota import DiversityQuota
    from .validator import FileValidator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FSTree:
    """Abstract class for file system tree representation."""

    tree: dict[str, set[os.DirEntry]]
    directories: tuple[str, ...]
    dir_idx_cycle: Iterator[int]


@dataclass(slots=True)
class FSTreeBuilder(ABC):
    """Scans the file system and builds a directory tree."""

    root: str
    validator: FileValidator
    rng: Random
    should_follow_symlink: bool

    @abstractmethod
    def build(self) -> Any:
        """Scan the root directory and build the directory tree."""


@dataclass(slots=True)
class RandomFSTreeBuilder(FSTreeBuilder):
    """Scans the file system and builds a directory tree with random order."""

    def build(self) -> FSTree:
        """Scan the root directory and build the directory tree."""
        logger.debug("Scanning root directory: %s", self.root)
        is_valid = self.validator.is_valid
        shuffle = self.rng.shuffle
        tree = {}
        for dirpath, _, filenames in walk_entries(self.root, follow_symlinks=self.should_follow_symlink):
            if not filenames:
                continue

            entries = [f for f in filenames if is_valid(f)]
            if entries:
                shuffle(entries)
                tree[dirpath] = set(entries)

        directories = tuple(tree.keys())
        valid_idx = list(range(len(directories)))
        shuffle(valid_idx)
        logger.debug("Completed scanning root directory.")
        return FSTree(
            tree=tree,
            directories=directories,
            dir_idx_cycle=itertools.cycle(valid_idx),
        )


@dataclass(slots=True)
class FSWalker(ABC):
    """Abstract file system walker."""

    @abstractmethod
    def walk(self) -> Iterator[os.DirEntry]:
        """Generate candidates for a given directory."""


@dataclass(slots=True)
class RandomFSWalker(FSWalker):
    """Navigates the file system randomly based on Quota rules."""

    tree: FSTree
    quota: DiversityQuota

    def walk(self) -> Iterator[os.DirEntry]:
        """Generate shuffled candidates for a given directory."""
        if not self.tree.directories:
            self.quota.lock_root()
            return

        _sc = self.tree
        _qu = self.quota
        directories = _sc.directories
        n_directories = len(directories)
        n_locked = 0
        is_dir_locked = _qu.is_dir_locked
        get_available = _qu.get_available
        lock_file = _qu.lock_file
        lock_dir = _qu.lock_dir
        tree = _sc.tree

        for di in _sc.dir_idx_cycle:
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
