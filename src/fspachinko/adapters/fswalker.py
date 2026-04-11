"""Filesystem walker adapter for FSPachinko."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os import scandir
from os.path import dirname, splitext
from typing import TYPE_CHECKING

from fspachinko.domain.model import FSEntry, FSPachinkoPin

if TYPE_CHECKING:
    import random
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AbstractFSWalker(ABC):
    """Abstract class for filesystem walker."""

    root: str
    should_follow_symlink: bool
    rng: random.Random

    @abstractmethod
    def __call__(self) -> Iterator[FSEntry]:
        """Walk the filesystem and return an iterator of FSEntry objects."""


@dataclass(slots=True)
class FSWalker(AbstractFSWalker):
    """Filesystem walker implementation."""

    _board: dict[str, FSPachinkoPin] = field(default_factory=dict, init=False, repr=False)

    def __call__(self) -> Iterator[FSEntry]:
        """Walk the filesystem and return an iterator of FSEntry objects."""
        _root = self.root
        curr = self.root
        _pop = self._board.pop
        _random = self.rng.random
        _choice = self.rng.choice
        while True:
            pin = self.pin_from_path(curr)
            if pin.is_empty:
                if curr == _root:
                    break
                _pop(curr)
                curr = _root
                continue
            if _random() < pin.subdir_total_ratio:  # Should descend
                curr = _choice(pin.subdirs)
                continue
            if files := pin.files:
                yield _choice(files)
            curr = _root

    def pin_from_path(self, path: str) -> FSPachinkoPin:
        """Add a new pin to the board, or return an existing one."""
        pin = self._board.setdefault(path, FSPachinkoPin(path=path))
        if not pin.is_scanned:
            self.scan_pin(pin)
        return pin

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
