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
    max_per_dir: int
    locked_dir: set[str] = field(default_factory=set)
    locked_file: set[os.DirEntry] = field(default_factory=set)
    dircount: Counter[str] = field(default_factory=Counter)

    def reset(self) -> None:
        """Reset batch-specific counters, optionally keeping file history."""
        self.dircount.clear()
        self.locked_dir.clear()

    def is_all_locked(self) -> bool:
        """Check if all files/folders are locked."""
        return self.root in self.locked_dir

    def is_dir_locked(self, directory: str) -> bool:
        """Check if a folder is locked."""
        return directory in self.locked_dir

    def is_file_locked(self, file: os.DirEntry) -> bool:
        """Check if a file is locked."""
        return file in self.locked_file

    def lock_dir(self, directory: str) -> None:
        """Mark a folder as locked without registering a success."""
        self.locked_dir.add(directory)

    def lock_file(self, file: os.DirEntry) -> None:
        """Mark a file as locked."""
        self.locked_file.add(file)

    def register_success(self, entry: os.PathLike) -> None:
        """Record a successful copy and apply locking rules."""
        if self.max_per_dir <= 0:
            return

        leaf_dir = os.path.dirname(entry)
        self.dircount[leaf_dir] += 1
        if self.dircount[leaf_dir] >= self.max_per_dir:
            self.lock_dir(leaf_dir)
