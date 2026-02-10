"""Quota and State management."""

from collections import Counter
from dataclasses import dataclass, field
from os.path import dirname
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from os import DirEntry

    from .walker import FSEntry


@dataclass(slots=True)
class DiversityQuota:
    """Manages rules for diversity (weights) and uniqueness."""

    max_per_dir: int | float
    is_create_unique_folders: bool

    locked_dir: set[str] = field(default_factory=set)
    locked_file: set[DirEntry] = field(default_factory=set)
    _dircount: Counter[str] = field(default_factory=Counter)

    def reset(self) -> None:
        """Reset the quota state for a new folder."""
        self._dircount.clear()
        self.locked_dir.clear()
        if not self.is_create_unique_folders:
            self.locked_file.clear()

    def update(self, entry: FSEntry) -> None:
        """Update the quota state after processing a file."""
        parent = dirname(entry.path)
        self._dircount[parent] += 1
        if self._dircount[parent] >= self.max_per_dir:
            self.locked_dir.add(parent)
