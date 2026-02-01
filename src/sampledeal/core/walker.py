"""Random file system navigator."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

from ..utils import WALKER_CACHE_LIMIT

if TYPE_CHECKING:
    from collections.abc import Iterator
    from random import Random

    from .quota import DiversityQuota

logger = logging.getLogger(__name__)


@lru_cache(maxsize=WALKER_CACHE_LIMIT)
def _get_entries(folder_path: str) -> tuple[os.DirEntry, ...]:
    """Retrieve directory entries for a given path."""
    try:
        with os.scandir(folder_path) as it:
            return tuple(it)
    except (PermissionError, OSError):
        logger.debug("Failed to access directory: %s", folder_path)
        return ()


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

    def walk(self) -> Iterator[os.DirEntry]:
        """Generate shuffled candidates for a given directory."""
        root_entries = self._get_shuffled_available_entries(self.root)
        if not root_entries:
            self.quota.lock_folder(self.root)
            return

        stack: list[str] = [self.root]
        cache: dict[str, set[os.DirEntry]] = {self.root: root_entries}

        while stack:
            folder_path = stack[-1]
            if self.quota.is_folder_locked(folder_path) or (entries := cache.get(folder_path)) is None:
                stack.pop()
                continue

            entry = entries.pop()
            if not entries:
                del cache[folder_path]

            # Handle symlinks
            if not self.should_follow_symlink and entry.is_symlink():
                self.quota.lock_entry(entry)
                continue

            # If it's a directory and has entries, add to stack
            if entry.is_dir():
                next_folder_path = entry.path
                if next_entries := self._get_shuffled_available_entries(next_folder_path):
                    cache[next_folder_path] = next_entries
                    stack.append(next_folder_path)
                continue

            # If it's a file, yield it
            if entry.is_file():
                self.quota.lock_file(entry.path)
                yield entry

        return

    def _get_shuffled_available_entries(self, folder_path: str) -> set[os.DirEntry]:
        """Get available entries for a directory, shuffled if multiple exist."""
        if not (entries := _get_entries(folder_path)):
            self.quota.lock_folder(folder_path)
            return set()

        if not (available := self.quota.get_available(entries)):
            self.quota.lock_folder(folder_path)
            return set()

        if len(available) > 1:
            self.rng.shuffle(available)

        return set(available)
