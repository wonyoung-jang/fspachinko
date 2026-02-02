"""Random file system navigator."""

import itertools
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os import fspath, scandir
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from random import Random

    from .quota import DiversityQuota

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
    _tree: dict[str, set[os.DirEntry]] = field(default_factory=dict)
    _valid_dirs: list[str] = field(default_factory=list)
    _valid_dirs_iter: Iterator[int] = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the walker by scanning the root directory."""
        logger.info("Scanning root directory: %s", self.root)
        self._scan_root()
        logger.info("Completed scanning root directory.")

    def _scan_root(self) -> None:
        """Scan the root directory and return its entries."""
        for dirpath, _, filenames in walk_entries(self.root, followlinks=self.should_follow_symlink):
            if f := filenames:
                self.rng.shuffle(f)
                self._tree[dirpath] = set(f)

        valid_dirs = list(self._tree.keys())
        self.rng.shuffle(valid_dirs)
        self._valid_dirs = valid_dirs
        self._valid_dirs_iter = itertools.cycle(range(len(self._valid_dirs)))

    def walk(self) -> Iterator[os.DirEntry]:
        """Generate shuffled candidates for a given directory."""
        if not self._valid_dirs:
            self.quota.lock_root()
            return

        for fi in self._valid_dirs_iter:
            dirpath = self._valid_dirs[fi]
            if self.quota.is_folder_locked(dirpath):
                continue

            if not (entries := self._tree[dirpath]):
                self.quota.lock_folder(dirpath)
                continue

            if not (available := self.quota.get_available(entries)):
                self.quota.lock_folder(dirpath)
                continue

            for entry in available:
                if not self.should_follow_symlink and entry.is_symlink():
                    self.quota.lock_file(entry)
                    continue

                self.quota.lock_file(entry)
                yield entry
                break


def walk_entries(
    top: str, *, onerror: Any = None, followlinks: bool = False
) -> Iterator[tuple[str, list[os.DirEntry], list[os.DirEntry]]]:
    """Reimplement os.walk with topdown walk of DirEntry objects."""
    stack: list[str] = [fspath(top)]
    islink, join = os.path.islink, os.path.join
    while stack:
        top = stack.pop()
        if isinstance(top, tuple):
            yield top
            continue

        dirs: list[os.DirEntry] = []
        nondirs: list[os.DirEntry] = []
        try:
            with scandir(top) as entries:
                for entry in entries:
                    try:
                        if followlinks:
                            is_dir = entry.is_dir()
                        else:
                            is_dir = entry.is_dir(follow_symlinks=False) and not entry.is_junction()
                    except OSError:
                        is_dir = False

                    if is_dir:
                        dirs.append(entry)
                    else:
                        nondirs.append(entry)
        except OSError as error:
            if onerror is not None:
                onerror(error)
            continue

        yield top, dirs, nondirs
        for dir_item in reversed(dirs):
            new_path = join(top, dir_item.name)
            if followlinks or not islink(new_path):
                stack.append(new_path)
