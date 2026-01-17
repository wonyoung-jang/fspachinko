"""Quota and State management."""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DiversityQuota:
    """Manages rules for diversity (weights) and uniqueness."""

    root: Path

    unique_folders: bool = False
    limit_root_folder: int = 0
    limit_leaf_folder: int = 0

    locked_files: set[Path] = field(default_factory=set)
    locked_folders: set[Path] = field(default_factory=set)
    folder_counts: dict[Path, int] = field(default_factory=lambda: defaultdict(int))

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

    def is_available(self, path: Path, *, is_file: bool) -> bool:
        """Check if a file or folder is eligible for selection."""
        if is_file:
            return path not in self.locked_files
        return path not in self.locked_folders

    def register_success(self, file_path: Path) -> None:
        """Record a successful copy and apply locking rules."""
        self.lock_file(file_path)

        leaf_dir = file_path.parent
        self.update_and_lock(leaf_dir, self.limit_leaf_folder)
        logger.debug("Updating leaf: %s (%d)", leaf_dir, self.folder_counts[leaf_dir])

        if (parent := leaf_dir.parent) == self.root:
            self.update_and_lock(parent, self.limit_root_folder)
            logger.debug("Updating root: %s (%d)", parent, self.folder_counts[parent])

    def update_and_lock(self, folder: Path, limit: int) -> None:
        """Update folder count and lock if limit reached."""
        if limit <= 0:
            return

        self.folder_counts[folder] += 1
        if self.folder_counts[folder] >= limit:
            self.lock_folder(folder)
