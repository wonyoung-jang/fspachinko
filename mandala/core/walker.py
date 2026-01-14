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
        if entry.is_file():
            return cls(Path(entry.path), is_file=True, is_dir=False, size=entry.stat().st_size)
        return cls(Path(entry.path), is_file=False, is_dir=True, size=0)


@dataclass(slots=True)
class RandomFSWalker:
    """Navigates the file system randomly based on Quota rules."""

    root: Path
    quota: DiversityQuota
    rng: Random
    trash_empty_folders: bool = False
    cache: dict[Path, tuple[FSEntry, ...]] = field(default_factory=dict)

    def generate_candidates(self) -> Iterator[FSEntry]:
        """Generate shuffled candidates for a given directory."""
        while True:
            if result := self.recursive_pick(self.root):
                yield result
            else:
                break

    def recursive_pick(self, current: Path) -> FSEntry | None:
        """Recursively descend directories finding a valid file."""
        entries = self._get_entries(current)
        if not entries:
            self.quota.lock_folder(current)
            return None

        indices = list(range(len(entries)))
        self.rng.shuffle(indices)

        for i in indices:
            entry = entries[i]

            if entry.is_file:
                self.quota.lock_file(entry.path)
                return entry

            if entry.is_dir and (next_entry := self.recursive_pick(entry.path)):
                return next_entry

        return None

    def _get_entries(self, path: Path) -> tuple[FSEntry, ...] | None:
        """Retrieve and cache directory entries for a given path."""
        if path not in self.cache:
            try:
                entries = ()
                with os.scandir(path) as it:
                    entries = tuple(FSEntry.from_scandir(e) for e in it)
                self.cache[path] = entries
            except (PermissionError, OSError):
                self.cache[path] = ()
                return None

        if not (items := self.cache[path]):
            trash_path(path, condition=self.trash_empty_folders)
            return None

        available = tuple(e for e in items if self.quota.is_available(e.path))
        return available if available else None
