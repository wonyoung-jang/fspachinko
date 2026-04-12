"""Filesystem walker adapter for FSPachinko."""

import contextlib
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

    _board: dict[str, FSPachinkoPin] = field(default_factory=dict)

    def __call__(self) -> Iterator[FSEntry]:
        """Walk the filesystem and return an iterator of FSEntry objects."""
        _curr = self.root
        _pop = self._board.pop
        _randint = self.rng.randint
        _random = self.rng.random
        _choice = self.rng.choice
        while True:
            pin = self.pin_from_path(_curr)
            if len(pin) == 0:
                if _curr == self.root:
                    break
                _pop(_curr)
                parent = dirname(_curr)
                if parent in self._board:
                    with contextlib.suppress(ValueError):
                        self._board[parent].subdirs.remove(_curr)
                _curr = self.root
                continue
            if _random() < pin.subdir_total_ratio:  # Should descend
                _curr = _choice(pin.subdirs)
                continue
            if files := pin.files:
                idx = _randint(0, len(files) - 1)
                yield files.pop(idx)
            _curr = self.root

    def pin_from_path(self, path: str) -> FSPachinkoPin:
        """Add a new pin to the board, or return an existing one."""
        if path in self._board:
            return self._board[path]
        pin = FSPachinkoPin(path=path)
        self.scan_pin(pin)
        self._board[path] = pin
        return pin

    def scan_pin(self, pin: FSPachinkoPin) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
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
