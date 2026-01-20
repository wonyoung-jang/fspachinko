"""Trashing module for Mandala."""

from __future__ import annotations

import logging
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from send2trash import send2trash

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TrashHandler:
    """Handles trashing of files and folders."""

    empty_folders: bool = False
    dry_run: bool = False
    empty_folders_to_trash: set[Path] = field(default_factory=set)

    def collect_empty_folder(self, path: Path) -> None:
        """Collect folder paths to be trashed later."""
        if self.empty_folders:
            self.empty_folders_to_trash.add(path)

    def execute_trash(self) -> None:
        """Trash all collected paths."""
        if self.dry_run:
            logger.info("Dry run enabled; skipping trashing files and folders")
            logger.info("Empty folders to trash: %s", "\n".join(str(p) for p in self.empty_folders_to_trash))
            return

        logger.info("Trashing collected files and folders")
        with suppress(Exception):
            send2trash(self.empty_folders_to_trash)
