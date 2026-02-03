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
    max_per_dir: int = 0
    locked_file: set[os.DirEntry] = field(default_factory=set)
    locked_dir: set[str] = field(default_factory=set)
    dircount: Counter[str] = field(default_factory=Counter)

    def prepare_for_batch(self) -> None:
        """Reset batch-specific counters, optionally keeping file history."""
        self.dircount.clear()
        self.locked_dir.clear()
        if not self.is_unique:
            self.locked_file.clear()

    def lock_root(self) -> None:
        """Lock the root folder."""
        self.locked_dir.add(self.root)

    def is_all_locked(self) -> bool:
        """Check if all files/folders are locked."""
        return self.root in self.locked_dir

    def is_dir_locked(self, directory: str) -> bool:
        """Check if a folder is locked."""
        return directory in self.locked_dir

    def lock_file(self, path: os.DirEntry) -> None:
        """Mark a file as used without registering a success."""
        self.locked_file.add(path)

    def lock_dir(self, directory: str) -> None:
        """Mark a folder as locked without registering a success."""
        self.locked_dir.add(directory)

    def get_available(self, entries: set[os.DirEntry]) -> set[os.DirEntry]:
        """Filter entries to only available files."""
        return entries.difference(self.locked_file)

    def register_success(self, entry: os.DirEntry) -> None:
        """Record a successful copy and apply locking rules."""
        if self.max_per_dir <= 0:
            return

        leaf_dir = os.path.dirname(entry)
        self.dircount[leaf_dir] += 1
        if self.dircount[leaf_dir] >= self.max_per_dir:
            self.lock_dir(leaf_dir)
            logger.debug("Locked directory: %s, count: %d", leaf_dir, self.dircount[leaf_dir])
