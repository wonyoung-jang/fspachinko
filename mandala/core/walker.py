"""Random file system navigator."""

import logging
import os
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ..utils.constants import WALKER_CACHE_LIMIT

if TYPE_CHECKING:
    from collections.abc import Iterator
    from random import Random

    from .quota import DiversityQuota

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FSEntry:
    """Represents a file system entry (file or directory)."""

    path: Path
    is_file: bool
    is_dir: bool
    size: int

    @classmethod
    def from_scandir(cls, entry: os.DirEntry, *, follow_symlinks: bool = False) -> FSEntry:
        """Create an FSEntry from a given Path."""
        is_file = entry.is_file(follow_symlinks=follow_symlinks)
        is_dir = entry.is_dir(follow_symlinks=follow_symlinks)
        size = entry.stat(follow_symlinks=follow_symlinks).st_size
        return cls(Path(entry.path), is_file=is_file, is_dir=is_dir, size=size)


@dataclass(slots=True)
class RandomFSWalker:
    """Navigates the file system randomly based on Quota rules."""

    root: Path
    quota: DiversityQuota
    rng: Random
    cache: OrderedDict[Path, tuple[FSEntry, ...]] = field(default_factory=OrderedDict)
    _cache_limit: int = WALKER_CACHE_LIMIT
    _stack: list[tuple[Path, list[FSEntry], int]] = field(default_factory=list)

    def walk(self) -> Iterator[FSEntry]:
        """Generate shuffled candidates for a given directory."""
        while (candidate := self._descend()) is not None:
            yield candidate

    def _descend(self) -> FSEntry | None:
        """Descend directories finding a valid file using an explicit stack."""
        self._stack.append((self.root, [], 0))

        while self._stack:
            path, available, idx = self._stack.pop()

            if idx >= len(available):
                entries = self._get_entries(path)

                # Conditions to lock folder:
                # - Directory is inaccessible
                # - Directory is empty
                # - No available entries
                if not entries or not (available := self.quota.get_available(entries)):
                    self.quota.lock_folder(path)
                    continue

                # Shuffle available entries
                if len(available) > 1:
                    self.rng.shuffle(available)
                idx = 0

            entry = available[idx]

            # Only push the next index if there are more entries
            if idx + 1 < len(available):
                self._stack.append((path, available, idx + 1))

            # Process the current entry
            if entry.is_file:
                self.quota.lock_file(entry.path)
                return entry

            # It's a directory, descend into
            if entry.is_dir:
                self._stack.append((entry.path, [], 0))

        return None

    def _get_entries(self, current: Path) -> tuple[FSEntry, ...]:
        """Retrieve and cache directory entries for a given path."""
        if current in self.cache:
            return self.cache[current]

        try:
            self.cache[current] = tuple(FSEntry.from_scandir(e) for e in os.scandir(current))
            if len(self.cache) > self._cache_limit:
                self.cache.popitem(last=False)
        except (PermissionError, OSError):
            logger.debug("Failed to access directory: %s", current)
            self.cache[current] = ()

        return self.cache[current]
