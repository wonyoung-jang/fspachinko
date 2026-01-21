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
    def from_scandir(cls, entry: os.DirEntry) -> FSEntry:
        """Create an FSEntry from a given Path."""
        is_file = entry.is_file()
        size = entry.stat().st_size
        return cls(Path(entry.path), is_file=is_file, is_dir=not is_file, size=size)


@dataclass(slots=True)
class RandomFSWalker:
    """Navigates the file system randomly based on Quota rules."""

    root: Path
    quota: DiversityQuota
    rng: Random
    trash: TrashHandler
    cache: dict[Path, tuple[FSEntry, ...]] = field(default_factory=dict)

    def generate_candidates(self) -> Iterator[FSEntry]:
        """Generate shuffled candidates for a given directory."""
        while True:
            candidate = self.descend_to_file()
            if candidate is None:
                break
            yield candidate

    def descend_to_file(self) -> FSEntry | None:
        """Descend directories finding a valid file using an explicit stack."""
        stack: list[tuple[Path, tuple[FSEntry, ...], list[int], int]] = [(self.root, (), [], 0)]

        while stack:
            path, available, indices, idx = stack[-1]

            if not available:
                if not (entries := self._get_entries(path)):
                    self.quota.lock_folder(path)
                    self.trash.collect_empty_folder(path)
                    stack.pop()
                    continue

                available = self.quota.get_available_entries(entries)
                if not available:
                    self.quota.lock_folder(path)
                    stack.pop()
                    continue

                indices = list(range(len(available)))
                self.rng.shuffle(indices)
                stack[-1] = (path, available, indices, 0)
                continue

            if idx < len(indices):
                entry = available[indices[idx]]
                stack[-1] = (path, available, indices, idx + 1)

                if entry.is_file:
                    self.quota.lock_file(entry.path)
                    return entry

                if entry.is_dir:
                    stack.append((entry.path, (), [], 0))
            else:
                stack.pop()

        return None

    def _get_entries(self, current: Path) -> tuple[FSEntry, ...]:
        """Retrieve and cache directory entries for a given path."""
        if current in self.cache:
            return self.cache[current]

        try:
            self.cache[current] = tuple(FSEntry.from_scandir(e) for e in os.scandir(current))
        except (PermissionError, OSError):
            self.cache[current] = ()

        return self.cache[current]
