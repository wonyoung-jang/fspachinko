"""Quota and State management."""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


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
        self.locked_files.add(file_path)

        # 1. Update Leaf Folder Quota
        leaf_dir = file_path.parent
        self.update_and_lock(leaf_dir, self.limit_leaf_folder)

        # 2. Update Root Subfolder Quota
        if self.limit_root_folder > 0 and leaf_dir != self.root:
            try:
                # Optimized: avoid .relative_to calculation if parent is root
                if leaf_dir.parent == self.root:
                    self.update_and_lock(leaf_dir, self.limit_root_folder)
                else:
                    # Deeply nested case
                    rel = file_path.relative_to(self.root)
                    top_folder = self.root / rel.parts[0]
                    self.update_and_lock(top_folder, self.limit_root_folder)
            except ValueError:
                pass

    def update_and_lock(self, folder: Path, limit: int) -> None:
        """Update folder count and lock if limit reached."""
        if limit <= 0:
            return

        self.folder_counts[folder] += 1
        if self.folder_counts[folder] >= limit:
            self.locked_folders.add(folder)
