"""Filesystem walker adapter for FSPachinko."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os import scandir
from os.path import dirname, splitext
from typing import TYPE_CHECKING

from fspachinko.domain.model import FSEntry, FSPachinkoPin

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AbstractFSWalker(ABC):
    """Abstract class for filesystem walker."""

    root: str
    should_follow_symlink: bool
    rng_random_fn: Callable
    rng_choice_fn: Callable

    @abstractmethod
    def __call__(self) -> Iterator[FSEntry]:
        """Walk the filesystem and return an iterator of FSEntry objects."""


@dataclass(slots=True)
class FSWalker(AbstractFSWalker):
    """Filesystem walker implementation."""

    board: dict[str, FSPachinkoPin] = field(default_factory=dict)

    def __call__(self) -> Iterator[FSEntry]:
        """Walk the filesystem and return an iterator of FSEntry objects."""
        if self.root not in self.board:
            self.get_pin(self.root)
        _root = self.root
        curr = self.root
        pop = self.board.pop
        _random = self.rng_random_fn
        _choice = self.rng_choice_fn
        while True:
            pin = self.get_pin(curr)
            if not pin.is_scanned:
                self.scan_pin(pin)
            if pin.is_empty and curr == _root:
                break
            if pin.is_empty:  # Reset pin to root
                pop(curr)
                curr = _root
                continue
            if _random() < pin.subdir_total_ratio:  # Should descend
                curr = _choice(pin.subdirs)
                continue
            if files := pin.files:
                yield _choice(files)
            curr = _root

    def get_pin(self, path: str) -> FSPachinkoPin:
        """Add a new pin to the board, or return an existing one."""
        return self.board.setdefault(path, FSPachinkoPin(path=path))

    def scan_pin(self, pin: FSPachinkoPin) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        pin.is_scanned = True
        try:
            with scandir(pin.path) as it:
                follow = self.should_follow_symlink
                append_subdir = pin.subdirs.append
                append_file = pin.files.append
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=follow):
                            append_subdir(e.path)
                        elif e.is_file(follow_symlinks=follow):
                            stat = e.stat(follow_symlinks=follow)
                            stem, ext = splitext(e.name)
                            append_file(
                                FSEntry(
                                    path=e.path,
                                    stem=stem,
                                    ext=ext,
                                    parent=dirname(e.path),
                                    size=stat.st_size,
                                    mtime=stat.st_mtime,
                                ),
                            )
                    except OSError:
                        logger.debug("Error accessing entry %s, skipping.", e.path)
        except OSError:
            logger.debug("Error scanning directory %s, skipping.", pin.path)
