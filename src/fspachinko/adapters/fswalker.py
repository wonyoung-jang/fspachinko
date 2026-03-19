"""Filesystem walker adapter for FSPachinko."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os import scandir
from os.path import dirname, splitext
from random import choice, random
from typing import TYPE_CHECKING

from fspachinko.domain.model import FSEntry, FSPachinkoPin

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class AbstractFSWalker(ABC):
    """Abstract class for filesystem walker."""

    @abstractmethod
    def __call__(self) -> Iterator[FSEntry]:
        """Walk the filesystem and return an iterator of FSEntry objects."""


@dataclass(slots=True)
class FSWalker(AbstractFSWalker):
    """Filesystem walker implementation."""

    root: str
    should_follow_symlink: bool
    board: dict[str, FSPachinkoPin] = field(default_factory=dict)

    def __call__(self) -> Iterator[FSEntry]:
        """Walk the filesystem and return an iterator of FSEntry objects."""
        if self.root not in self.board:
            self.get_pin(self.root)
        root = self.root
        curr = self.root
        pop = self.board.pop
        while True:
            pin = self.get_pin(curr)
            if not pin.is_scanned:
                self.scan_pin(pin)
            subdirs, files = pin.subdirs, pin.files
            if not subdirs and not files:
                if curr == root:
                    break
                pop(curr)
                curr = root
                continue
            n_files = len(files)
            n_subdirs = len(subdirs)
            total = n_files + n_subdirs
            should_descend = random() < n_subdirs / total if total > 0 else False
            if should_descend:
                curr = choice(subdirs)
                continue
            if files:
                yield choice(files)
            curr = root

    def get_pin(self, path: str) -> FSPachinkoPin:
        """Add a new pin to the board, or return an existing one."""
        return self.board.setdefault(path, FSPachinkoPin(path=path))

    def scan_pin(self, pin: FSPachinkoPin) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        follow = self.should_follow_symlink
        try:
            pin.is_scanned = True
            with scandir(pin.path) as it:
                subdirs_append = pin.subdirs.append
                files_append = pin.files.append
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=follow):
                            subdirs_append(e.path)
                        elif e.is_file(follow_symlinks=follow):
                            stat = e.stat(follow_symlinks=follow)
                            stem, ext = splitext(e.name)
                            files_append(
                                FSEntry(
                                    path=e.path,
                                    stem=stem,
                                    ext=ext,
                                    parent=dirname(e.path),
                                    size=stat.st_size,
                                    mtime=stat.st_mtime,
                                )
                            )
                    except OSError:
                        logger.debug("Error accessing entry %s, skipping.", e.path)
        except OSError:
            logger.debug("Error scanning directory %s, skipping.", pin.path)
