"""Random file system navigator."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ..core.helpers import trash_path

if TYPE_CHECKING:
    from collections.abc import Iterator
    from random import Random

    from .quota import DiversityQuota


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
        stats = entry.stat()
        return cls(
            path=Path(entry.path),
            is_file=entry.is_file(),
            is_dir=entry.is_dir(),
            size=stats.st_size if entry.is_file() else 0,
        )


@dataclass(slots=True)
class RandomFSWalker:
    """Navigates the file system randomly based on Quota rules."""

    root: Path
    quota: DiversityQuota
    rng: Random
    trash_empty_folders: bool = False
    cache: dict[Path, tuple[FSEntry, ...] | None] = field(default_factory=dict)

    def generate_candidates(self) -> Iterator[FSEntry]:
        """Generate shuffled candidates for a given directory."""
        while True:
            result = self.recursive_pick(self.root)
            if result:
                yield result
            else:
                return

    def recursive_pick(self, current: Path) -> FSEntry | None:
        """Recursively descend directories finding a valid file."""
        candidates = self._get_candidates(current)
        if not candidates:
            self.quota.lock_folder(current)
            return None

        indices = list(range(len(candidates)))
        self.rng.shuffle(indices)

        for i in indices:
            candidate = candidates[i]

            if candidate.is_file:
                self.quota.lock_file(candidate.path)
                return candidate

            if candidate.is_dir:
                found = self.recursive_pick(candidate.path)
                if found:
                    return found

        return None

    def _get_candidates(self, path: Path) -> tuple[FSEntry, ...] | None:
        """Retrieve and cache directory entries for a given path."""
        if path not in self.cache:
            try:
                entries = ()
                with os.scandir(path) as scanner:
                    entries = tuple(FSEntry.from_scandir(entry) for entry in scanner)

                if not entries:
                    self.cache[path] = None
                else:
                    self.cache[path] = entries
            except (PermissionError, OSError):
                self.cache[path] = None

        items = self.cache[path]
        if items is None:
            trash_path(path, condition=self.trash_empty_folders)
            return None

        available = tuple(e for e in items if self.quota.is_available(e.path))
        return available if available else None
