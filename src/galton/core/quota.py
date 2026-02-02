"""Quota and State management."""

import logging
import os
from collections import Counter
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DiversityQuota:
    """Manages rules for diversity (weights) and uniqueness."""

    root: str
    is_unique: bool = False
    max_per_folder: int = 0
    locked_files: set[os.DirEntry] = field(default_factory=set)
    locked_folders: set[str] = field(default_factory=set)
    folder_counts: Counter[str] = field(default_factory=Counter)

    def prepare_for_batch(self) -> None:
        """Reset batch-specific counters, optionally keeping file history."""
        self.folder_counts.clear()
        self.locked_folders.clear()
        if not self.is_unique:
            self.locked_files.clear()

    def lock_root(self) -> None:
        """Lock the root folder."""
        self.locked_folders.add(self.root)

    def is_all_locked(self) -> bool:
        """Check if all files/folders are locked."""
        return self.root in self.locked_folders

    def is_folder_locked(self, folder_path: str) -> bool:
        """Check if a folder is locked."""
        return folder_path in self.locked_folders

    def lock_file(self, path: os.DirEntry) -> None:
        """Mark a file as used without registering a success."""
        self.locked_files.add(path)

    def lock_folder(self, folder_path: str) -> None:
        """Mark a folder as locked without registering a success."""
        self.locked_folders.add(folder_path)

    def get_available(self, entries: set[os.DirEntry]) -> set[os.DirEntry]:
        """Filter entries to only available files."""
        return entries.difference(self.locked_files)

    def register_success(self, file_path: str) -> None:
        """Record a successful copy and apply locking rules."""
        leaf_dir = os.path.dirname(file_path)
        if self.max_per_folder > 0:
            self.folder_counts[leaf_dir] += 1
            if self.folder_counts[leaf_dir] >= self.max_per_folder:
                self.lock_folder(leaf_dir)

            logger.debug("Updating leaf: %s (%d)", leaf_dir, self.folder_counts[leaf_dir])
