"""Random file system navigator."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os import scandir
from os.path import dirname, splitext
from random import choice
from typing import TYPE_CHECKING

from ..domain.model import FSEntry, FSPachinkoPin

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class AbstractFSWalker(ABC):
    """Abstract file system walker."""

    @abstractmethod
    def walk(self) -> Iterator[FSEntry]:
        """Generate candidates for a given directory."""


@dataclass(slots=True)
class PachinkoFSWalker(AbstractFSWalker):
    """Simulates a Pachinko machine.

    For every file needed, we 'drop' a search cursor from the Root.
    It bounces randomly down directory paths until it settles on a file.
    """

    root: str
    should_follow_symlink: bool
    board: dict[str, FSPachinkoPin] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize the board with the root pin."""
        self.get(self.root)

    def walk(self) -> Iterator[FSEntry]:
        """Iterate through FSEntry objects."""
        root = self.root
        curr = self.root
        get = self.get
        pop = self.board.pop

        while True:
            pin = get(curr)
            if not pin.is_scanned:
                self.scan(pin)

            subdirs, files = pin.subdirs, pin.files

            if not subdirs and not files:
                if curr == root:
                    break
                pop(curr)
                curr = root
                continue

            should_descend = choice((True, False)) if subdirs and files else bool(subdirs)
            if should_descend:
                curr = choice(subdirs)
                continue

            if files:
                yield choice(files)

            curr = root

    def get(self, path: str) -> FSPachinkoPin:
        """Add a new pin to the board, or return an existing one."""
        return self.board.setdefault(path, FSPachinkoPin(path=path))

    def scan(self, pin: FSPachinkoPin) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        try:
            pin.is_scanned = True
            with scandir(pin.path) as it:
                follow = self.should_follow_symlink
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
                        continue
        except OSError:
            logger.debug("Error scanning directory %s, skipping.", pin.path)
            return
