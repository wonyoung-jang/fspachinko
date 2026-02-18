"""File transfer strategies."""

import os
from dataclasses import dataclass
from io import UnsupportedOperation
from os import PathLike, link, symlink, unlink
from shutil import copy, copy2, move
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any

from .constants import FileError, TransferMode

if TYPE_CHECKING:
    from collections.abc import Callable


def get_available_transfer_modes() -> tuple[TransferMode, ...]:
    """Detect which transfer modes are supported on the current OS."""
    # COPY and MOVE are always available
    available = [TransferMode.COPY, TransferMode.COPY_PRESERVE, TransferMode.MOVE]

    def _test_link_creation(link_func: Callable[[str, str], None]) -> None:
        """Test link creation."""
        test_src = os.path.join(tmpdir, "test_src")
        test_link = os.path.join(tmpdir, "test_link")
        open(test_src, "w").close()
        link_func(test_src, test_link)
        unlink(test_link)
        unlink(test_src)

    # SYMLINK availability
    try:
        with TemporaryDirectory() as tmpdir:
            _test_link_creation(symlink)
        available.append(TransferMode.SYMLINK)
    except OSError, UnsupportedOperation, NotImplementedError:
        pass

    # HARDLINK availability
    try:
        with TemporaryDirectory() as tmpdir:
            _test_link_creation(link)
        available.append(TransferMode.HARDLINK)
    except OSError, UnsupportedOperation, NotImplementedError:
        pass

    return tuple(available)


def get_transfer_strategy(mode: str) -> Callable[[PathLike[str], str], None]:
    """Return the appropriate transfer strategy instance.

    Falls back to SYMLINK if the requested mode is not available.
    Falls back to COPY if SYMLINK is not available.
    """
    mapping: dict[TransferMode, Any] = {
        TransferMode.COPY: CopyTransfer(),
        TransferMode.COPY_PRESERVE: CopyPreserveTransfer(),
        TransferMode.MOVE: MoveTransfer(),
        TransferMode.SYMLINK: SymlinkTransfer(),
        TransferMode.HARDLINK: HardlinkTransfer(),
    }
    available = get_available_transfer_modes()
    requested = TransferMode(mode)
    if requested in available:
        return mapping[requested]
    if TransferMode.SYMLINK in available:
        return mapping[TransferMode.SYMLINK]
    return mapping[TransferMode.COPY]


def hardlink(src: PathLike[str], dst: str) -> None:
    """Create a hardlink from source to destination.

    Falls back to symlink if hardlinking across filesystems fails.
    """
    try:
        link(src, dst)
    except OSError as e:
        if e.winerror == FileError.WINDOWS_CROSS_DRIVE_ERROR or e.errno == FileError.UNIX_CROSS_FILESYSTEM_ERROR:
            symlink(src, dst)
        else:
            raise


@dataclass(slots=True)
class CopyTransfer:
    """Represents a copy file transfer operation."""

    def __call__(self, src: PathLike[str], dst: str) -> None:
        """Copy the file from source to destination."""
        copy(src, dst)


@dataclass(slots=True)
class CopyPreserveTransfer:
    """Represents a copy with metadata preservation file transfer operation."""

    def __call__(self, src: PathLike[str], dst: str) -> None:
        """Copy the file from source to destination while preserving metadata."""
        copy2(src, dst)


@dataclass(slots=True)
class MoveTransfer:
    """Represents a move file transfer operation."""

    def __call__(self, src: PathLike[str], dst: str) -> None:
        """Move the file from source to destination."""
        move(src, dst)


@dataclass(slots=True)
class SymlinkTransfer:
    """Represents a symbolic link file transfer operation."""

    def __call__(self, src: PathLike[str], dst: str) -> None:
        """Create a symbolic link from source to destination."""
        symlink(src, dst)


@dataclass(slots=True)
class HardlinkTransfer:
    """Represents a hard link file transfer operation."""

    def __call__(self, src: PathLike[str], dst: str) -> None:
        """Create a hard link from source to destination."""
        hardlink(src, dst)
