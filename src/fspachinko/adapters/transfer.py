"""File transfer strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import UnsupportedOperation
from os import link, symlink, unlink
from os.path import join
from shutil import copy, copy2, move
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ..constants import FileError, TransferMode

if TYPE_CHECKING:
    from collections.abc import Callable


def get_available_transfer_modes() -> dict[TransferMode, AbstractTransfer]:
    """Return the set of available transfer modes based on the current environment."""
    available = {
        TransferMode.DRY_RUN: DryRunTransfer(),
        TransferMode.COPY: CopyTransfer(),
        TransferMode.COPY_PRESERVE: CopyPreserveTransfer(),
        TransferMode.MOVE: MoveTransfer(),
        TransferMode.SYMLINK: SymlinkTransfer(),
        TransferMode.HARDLINK: HardlinkTransfer(),
    }

    def _verify_link_fn(link_func: Callable[[str, str], None], transfer_mode: TransferMode) -> None:
        """Test link creation."""
        try:
            with TemporaryDirectory() as tmpdir:
                test_src = join(tmpdir, "test_src")
                test_link = join(tmpdir, "test_link")
                open(test_src, "w").close()
                link_func(test_src, test_link)
                unlink(test_link)
                unlink(test_src)
        except OSError, UnsupportedOperation, NotImplementedError:
            available.pop(transfer_mode)

    _verify_link_fn(symlink, TransferMode.SYMLINK)
    _verify_link_fn(link, TransferMode.HARDLINK)
    return available


def get_transfer_fn(mode: str) -> AbstractTransfer:
    """Return the appropriate transfer strategy instance.

    Falls back to DRY_RUN if the requested mode is not available.
    """
    available = get_available_transfer_modes()
    return available.get(TransferMode(mode), available[TransferMode.DRY_RUN])


class AbstractTransfer(ABC):
    """Abstract base class for file transfer strategies."""

    @abstractmethod
    def __call__(self, src: str, dst: str) -> None:
        """Perform the file transfer operation."""


@dataclass(slots=True)
class DryRunTransfer(AbstractTransfer):
    """Represents a dry-run file transfer operation."""

    def __call__(self, src: str, dst: str) -> None:
        """Do nothing (dry-run)."""


@dataclass(slots=True)
class CopyTransfer(AbstractTransfer):
    """Represents a copy file transfer operation."""

    def __call__(self, src: str, dst: str) -> None:
        """Copy the file from source to destination."""
        copy(src, dst)


@dataclass(slots=True)
class CopyPreserveTransfer(AbstractTransfer):
    """Represents a copy with metadata preservation file transfer operation."""

    def __call__(self, src: str, dst: str) -> None:
        """Copy the file from source to destination while preserving metadata."""
        copy2(src, dst)


@dataclass(slots=True)
class MoveTransfer(AbstractTransfer):
    """Represents a move file transfer operation."""

    def __call__(self, src: str, dst: str) -> None:
        """Move the file from source to destination."""
        move(src, dst)


@dataclass(slots=True)
class SymlinkTransfer(AbstractTransfer):
    """Represents a symbolic link file transfer operation."""

    def __call__(self, src: str, dst: str) -> None:
        """Create a symbolic link from source to destination."""
        symlink(src, dst)


@dataclass(slots=True)
class HardlinkTransfer(AbstractTransfer):
    """Represents a hard link file transfer operation."""

    def __call__(self, src: str, dst: str) -> None:
        """Create a hardlink from source to destination."""
        try:
            link(src, dst)
        except OSError as e:
            is_win_x_error = e.winerror == FileError.WINDOWS_CROSS_DRIVE_ERROR
            is_unix_x_error = e.errno == FileError.UNIX_CROSS_FILESYSTEM_ERROR
            if is_win_x_error or is_unix_x_error:
                symlink(src, dst)
            else:
                raise
