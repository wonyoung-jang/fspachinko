"""Random file system navigator."""

import logging
import os
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..utils import WALKER_CACHE_LIMIT

if TYPE_CHECKING:
    from collections.abc import Iterator
    from random import Random

    from .quota import DiversityQuota

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FSEntry:
    """Represents a file system entry (file or directory)."""

    _entry: os.DirEntry
    _is_file: bool | None = None
    _is_dir: bool | None = None
    _is_symlink: bool | None = None
    _size: int | None = None

    @property
    def name(self) -> str:
        """Get the name of the entry."""
        return self._entry.name

    @property
    def path(self) -> str:
        """Get the path of the entry."""
        return self._entry.path

    @property
    def is_file(self) -> bool:
        """Check if the entry is a file."""
        if self._is_file is not None:
            return self._is_file
        self._is_file = self._entry.is_file()
        return self._is_file

    @property
    def is_dir(self) -> bool:
        """Check if the entry is a directory."""
        if self._is_dir is not None:
            return self._is_dir
        self._is_dir = self._entry.is_dir()
        return self._is_dir

    @property
    def is_symlink(self) -> bool:
        """Check if the entry is a symlink."""
        if self._is_symlink is not None:
            return self._is_symlink
        self._is_symlink = self._entry.is_symlink()
        return self._is_symlink

    @property
    def size(self) -> int:
        """Get the size of the entry."""
        if self._size is not None:
            return self._size
        self._size = self._entry.stat().st_size
        return self._size


@dataclass(slots=True)
class FSWalker(ABC):
    """Abstract file system walker."""

    @abstractmethod
    def walk(self) -> Iterator[FSEntry]:
        """Generate candidates for a given directory."""


@dataclass(slots=True)
class RandomFSWalker(FSWalker):
    """Navigates the file system randomly based on Quota rules."""

    root: str
    quota: DiversityQuota
    rng: Random
    follow_symlinks: bool

    _cache_limit: int = WALKER_CACHE_LIMIT
    _cache: OrderedDict[str, tuple[FSEntry, ...]] = field(default_factory=OrderedDict)

    def walk(self) -> Iterator[FSEntry]:
        """Generate shuffled candidates for a given directory."""
        while (candidate := self._descend()) is not None:
            yield candidate

    def _descend(self) -> FSEntry | None:
        """Descend directories finding a valid file using an explicit stack."""
        _stack: list[tuple[str, list[FSEntry], int]] = [(self.root, [], 0)]

        while _stack:
            entry_root, available, idx = _stack.pop()

            if idx >= len(available):
                if not (entries := self._get_entries(entry_root)):
                    self.quota.lock_folder(entry_root)
                    continue

                if not (available := self.quota.get_available(entries)):
                    self.quota.lock_folder(entry_root)
                    continue

                if len(available) > 1:
                    self.rng.shuffle(available)
                idx = 0

            entry = available[idx]

            # Only push the next index if there are more entries
            if idx + 1 < len(available):
                _stack.append((entry_root, available, idx + 1))

            # If it's a file, return it
            if entry.is_file:
                # Skip symlinks if not following them
                if not self.follow_symlinks and entry.is_symlink:
                    self.quota.lock_file(entry.path)
                    continue

                self.quota.lock_file(entry.path)
                return entry

            # It's a directory, descend into
            if entry.is_dir:
                # Skip symlinks if not following them
                if not self.follow_symlinks and entry.is_symlink:
                    self.quota.lock_folder(entry.path)
                    continue

                _stack.append((entry.path, [], 0))

        return None

    def _get_entries(self, current: str) -> tuple[FSEntry, ...]:
        """Retrieve and cache directory entries for a given path."""
        if current in self._cache:
            return self._cache[current]

        try:
            self._cache[current] = tuple(FSEntry(e) for e in os.scandir(current))
        except (PermissionError, OSError):
            logger.debug("Failed to access directory: %s", current)
            self._cache[current] = ()

        if len(self._cache) > self._cache_limit:
            self._cache.popitem(last=False)

        return self._cache[current]
