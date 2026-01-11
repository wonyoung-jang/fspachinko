"""Random file system navigator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..core.helpers import trash_path

if TYPE_CHECKING:
    from pathlib import Path
    from random import Random

    from .quota import DiversityQuota


@dataclass(slots=True)
class RandomFSWalker:
    """Navigates the file system randomly based on Quota rules."""

    root: Path
    quota: DiversityQuota
    rng: Random
    trash_empty_folders: bool = False
    directory_cache: dict[Path, tuple[Path, ...] | None] = field(default_factory=dict)

    def get_next_file(self) -> Path | None:
        """Entry point: starts a fresh random descent from Root."""
        return self.recursive_pick(self.root)

    def recursive_pick(self, current: Path) -> Path | None:
        """Recursively descend directories finding a valid file."""
        if current not in self.directory_cache:
            self._populate_cache(current)

        children = self.directory_cache[current]
        if children is None:
            trash_path(current, condition=self.trash_empty_folders)
            return None

        candidates = [p for p in children if self.quota.is_available(p) and (p.is_file() or self._is_dir_available(p))]
        if not candidates:
            self.quota.lock_folder(current)
            return None

        candidate = self.rng.choice(candidates)
        if candidate.is_file():
            self.quota.lock_file(candidate)
            return candidate

        if candidate.is_dir():
            result = self.recursive_pick(candidate)
            if result is not None:
                return result

            return self.recursive_pick(current)
        return None

    def _is_dir_available(self, path: Path) -> bool:
        """Quick check if a directory is theoretically enterable.

        Does cached check without forcing a full scan
        If cache exists and is None, it's exhausted/permission error
        """
        return not (path in self.directory_cache and self.directory_cache[path] is None)

    def _populate_cache(self, path: Path) -> None:
        """Populate the cache for a given directory path.

        Filter for file/dir immediately to reduce list size
        """
        try:
            items = tuple(p for p in path.glob("*"))
            if not items:
                self.directory_cache[path] = None  # Empty
            else:
                self.directory_cache[path] = items
        except (PermissionError, OSError):
            self.directory_cache[path] = None
