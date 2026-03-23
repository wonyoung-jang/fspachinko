"""File transfer adapter."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from io import UnsupportedOperation
from os import link, symlink, unlink
from os.path import join
from shutil import copy, copy2, move
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from fspachinko.constants import OSCrossError, TransferMode

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AbstractTransferFnManager(ABC):
    """Abstract class for file transfer."""

    @abstractmethod
    def get(self, mode: TransferMode) -> Callable:
        """Get the transfer function for the specified mode."""


@dataclass(slots=True)
class FileTransferFnManager(AbstractTransferFnManager):
    """File transfer implementation."""

    available: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize the available transfer modes."""
        self.available.update(TRANSFER_FNS)
        for mode, fn in LINK_FNS.items():
            if not _link_fn_is_available(fn):
                self.available.pop(mode, None)

    @property
    def transfermodes(self) -> tuple[str, ...]:
        """Return the set of available transfer modes."""
        return tuple(self.available.keys())

    def get(self, mode: str) -> Callable:
        """Get the transfer function for the specified mode."""
        return self.available.get(mode, self.available[TransferMode.DRY_RUN])


def hardlink(src: str, dst: str) -> None:
    """Create a hardlink from source to destination."""
    try:
        link(src, dst)
    except OSError as e:
        if e.winerror == OSCrossError.WINDOWS or e.errno == OSCrossError.UNIX:
            symlink(src, dst)
        else:
            raise


def _link_fn_is_available(link_fn: Callable) -> bool:
    """Test if a link function works in the current environment."""
    try:
        with TemporaryDirectory() as tmpdir:
            test_src = join(tmpdir, "test_src")
            test_link = join(tmpdir, "test_link")
            open(test_src, "w").close()
            link_fn(test_src, test_link)
            unlink(test_link)
            unlink(test_src)
    except OSError, UnsupportedOperation, NotImplementedError:
        return False
    return True


TRANSFER_FNS: dict[str, Callable] = {
    TransferMode.DRY_RUN: lambda _src, _dst: None,
    TransferMode.COPY: copy,
    TransferMode.COPY_PRESERVE: copy2,
    TransferMode.MOVE: move,
    TransferMode.SYMLINK: symlink,
    TransferMode.HARDLINK: hardlink,
}

LINK_FNS: dict[str, Callable] = {
    TransferMode.SYMLINK: symlink,
    TransferMode.HARDLINK: link,
}
