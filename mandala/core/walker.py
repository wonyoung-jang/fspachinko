"""Random file system navigator."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from random import Random

    from .quota import DiversityQuota
    from .trash import TrashHandler

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
        size = entry.stat(follow_symlinks=follow_symlinks).st_size
        return cls(Path(entry.path), is_file=is_file, is_dir=not is_file, size=size)


@dataclass(slots=True)
class RandomFSWalker:
    """Navigates the file system randomly based on Quota rules."""

    root: Path
    quota: DiversityQuota
    rng: Random
    trash: TrashHandler
    cache: dict[Path, tuple[FSEntry, ...] | None] = field(default_factory=dict)

    def generate_candidates(self) -> Iterator[FSEntry]:
        """Generate shuffled candidates for a given directory."""
        while (candidate := self.descend_to_file()) is not None:
            yield candidate

    def descend_to_file(self) -> FSEntry | None:
        """Descend directories finding a valid file using an explicit stack."""
        stack: list[tuple[Path, list[FSEntry], int]] = [(self.root, [], 0)]

        while stack:
            path, available, idx = stack.pop()

            if idx >= len(available):
                entries = self._get_entries(path)

                # Directory is inaccessible, lock, do not trash
                if entries is None:
                    self.quota.lock_folder(path)
                    continue

                # Directory is empty, trash if configured
                if len(entries) == 0:
                    self.quota.lock_folder(path)
                    self.trash.collect_empty_folder(path)
                    continue

                # No available entries, lock
                if not (available := self.quota.get_available(entries)):
                    self.quota.lock_folder(path)
                    continue

                # Shuffle available entries
                if len(available) > 1:
                    self.rng.shuffle(available)
                idx = 0

            entry = available[idx]

            # Only push the next index if there are more entries
            if idx + 1 < len(available):
                stack.append((path, available, idx + 1))

            # Process the current entry
            if entry.is_file:
                return entry

            # It's a directory, descend into
            if entry.is_dir:
                stack.append((entry.path, [], 0))

        return None

    def _get_entries(self, current: Path) -> tuple[FSEntry, ...] | None:
        """Retrieve and cache directory entries for a given path."""
        if current in self.cache:
            return self.cache[current]

        try:
            self.cache[current] = tuple(FSEntry.from_scandir(e) for e in os.scandir(current))
        except (PermissionError, OSError):
            logger.debug("Failed to access directory: %s", current)
            self.cache[current] = None

        return self.cache[current]
