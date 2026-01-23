"""Quota and State management."""

import logging
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .walker import FSEntry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DiversityQuota:
    """Manages rules for diversity (weights) and uniqueness."""

    root: Path

    unique_folders: bool = False
    max_per_folder: int = 0

    locked_files: set[Path] = field(default_factory=set)
    locked_folders: set[Path] = field(default_factory=set)
    folder_counts: Counter[Path] = field(default_factory=Counter)

    def prepare_for_batch(self) -> None:
        """Reset batch-specific counters, optionally keeping file history."""
        self.folder_counts.clear()
        self.locked_folders.clear()
        if not self.unique_folders:
            self.locked_files.clear()

    def all_locked(self) -> bool:
        """Check if all files/folders are locked."""
        return self.root in self.locked_folders

    def lock_file(self, file_path: Path) -> None:
        """Mark a file as used without registering a success."""
        self.locked_files.add(file_path)

    def lock_folder(self, folder_path: Path) -> None:
        """Mark a folder as locked without registering a success."""
        self.locked_folders.add(folder_path)

    def get_available(self, entries: Iterable[FSEntry]) -> list[FSEntry]:
        """Filter entries to only those that are available."""
        return [e for e in entries if self.is_available(e.path, is_file=e.is_file)]

    def is_available(self, path: Path, *, is_file: bool) -> bool:
        """Check if a file or folder is eligible for selection."""
        if is_file:
            return path not in self.locked_files
        return path not in self.locked_folders

    def register_success(self, file_path: Path) -> None:
        """Record a successful copy and apply locking rules."""
        leaf_dir = file_path.parent
        if self.max_per_folder > 0:
            self.folder_counts[leaf_dir] += 1
            if self.folder_counts[leaf_dir] >= self.max_per_folder:
                self.lock_folder(leaf_dir)

            logger.debug("Updating leaf: %s (%d)", leaf_dir, self.folder_counts[leaf_dir])
