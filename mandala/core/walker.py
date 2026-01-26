"""Random file system navigator."""

import logging
import os
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ..utils import WALKER_CACHE_LIMIT

if TYPE_CHECKING:
    from collections.abc import Iterator
    from random import Random

    from .quota import DiversityQuota

logger = logging.getLogger(__name__)


@dataclass(slots=True, unsafe_hash=True)
class FSEntry:
    """Represents a file system entry (file or directory)."""

    path: Path
    is_file: bool
    is_dir: bool
    is_symlink: bool
    size: int

    @classmethod
    def from_scandir(cls, entry: os.DirEntry) -> FSEntry:
        """Create an FSEntry from a given Path."""
        return cls(
            Path(entry.path),
            is_file=entry.is_file(),
            is_dir=entry.is_dir(),
            is_symlink=entry.is_symlink(),
            size=entry.stat().st_size,
        )


@dataclass(slots=True)
class FSWalker(ABC):
    """Abstract file system walker."""

    @abstractmethod
    def walk(self) -> Iterator[FSEntry]:
        """Generate candidates for a given directory."""


@dataclass(slots=True)
class RandomFSWalker(FSWalker):
    """Navigates the file system randomly based on Quota rules."""

    root: Path
    quota: DiversityQuota
    rng: Random
    follow_symlinks: bool

    _cache_limit: int = WALKER_CACHE_LIMIT
    _cache: OrderedDict[Path, tuple[FSEntry, ...]] = field(default_factory=OrderedDict)
    _stack: list[tuple[Path, list[FSEntry], int]] = field(default_factory=list)

    def walk(self) -> Iterator[FSEntry]:
        """Generate shuffled candidates for a given directory."""
        while (candidate := self._descend()) is not None:
            yield candidate

    def _descend(self) -> FSEntry | None:
        """Descend directories finding a valid file using an explicit stack."""
        _stack: list[tuple[Path, list[FSEntry], int]] = [(self.root, [], 0)]

        while _stack:
            path, available, idx = _stack.pop()

            if idx >= len(available):
                if not (entries := self._get_entries(path)):
                    self.quota.lock_folder(path)
                    continue

                if not (available := self.quota.get_available(entries)):
                    self.quota.lock_folder(path)
                    continue

                if len(available) > 1:
                    self.rng.shuffle(available)
                idx = 0

            entry = available[idx]

            # Only push the next index if there are more entries
            if idx + 1 < len(available):
                _stack.append((path, available, idx + 1))

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

    def _get_entries(self, current: Path) -> tuple[FSEntry, ...]:
        """Retrieve and cache directory entries for a given path."""
        if current in self._cache:
            return self._cache[current]

        try:
            self._cache[current] = tuple(FSEntry.from_scandir(e) for e in os.scandir(current))
        except (PermissionError, OSError):
            logger.debug("Failed to access directory: %s", current)
            self._cache[current] = ()

        if len(self._cache) > self._cache_limit:
            self._cache.popitem(last=False)

        return self._cache[current]
