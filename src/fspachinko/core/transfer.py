"""File transfer strategies."""

import os
import shutil
from io import UnsupportedOperation
from os import PathLike
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ..utils import FileError, TransferMode

if TYPE_CHECKING:
    from collections.abc import Callable


def get_available_transfer_modes() -> tuple[TransferMode, ...]:
    """Detect which transfer modes are supported on the current OS."""
    # COPY and MOVE are always available
    available = [TransferMode.COPY, TransferMode.COPY_PRESERVE, TransferMode.MOVE]

    # SYMLINK availability
    try:
        with TemporaryDirectory() as tmpdir:
            test_src = os.path.join(tmpdir, "test_src")
            test_dst = os.path.join(tmpdir, "test_symlink")
            open(test_src, "w").close()
            os.symlink(test_src, test_dst)
            os.unlink(test_dst)
            os.unlink(test_src)
        available.append(TransferMode.SYMLINK)
    except (OSError, UnsupportedOperation, NotImplementedError):
        pass

    # HARDLINK availability
    try:
        with TemporaryDirectory() as tmpdir:
            test_src = os.path.join(tmpdir, "test_src")
            test_dst = os.path.join(tmpdir, "test_hardlink")
            open(test_src, "w").close()
            os.link(test_src, test_dst)
            os.unlink(test_dst)
            os.unlink(test_src)
        available.append(TransferMode.HARDLINK)
    except (OSError, UnsupportedOperation, NotImplementedError):
        pass

    return tuple(available)


def fetch_transfer_strategy(mode: str) -> Callable[[PathLike, str], None]:
    """Return the appropriate transfer strategy instance.

    Falls back to SYMLINK if the requested mode is not available.
    """
    strategy_map = {
        TransferMode.COPY: transfer_copy,
        TransferMode.COPY_PRESERVE: transfer_copy_preserve,
        TransferMode.MOVE: transfer_move,
        TransferMode.SYMLINK: transfer_symlink,
        TransferMode.HARDLINK: transfer_hardlink,
    }
    available_modes = get_available_transfer_modes()
    requested_mode = TransferMode(mode)
    if requested_mode in available_modes:
        return strategy_map[requested_mode]
    return transfer_symlink


def transfer_copy(src: PathLike, dst: str) -> None:
    """Copy a file from source to destination."""
    shutil.copy(src, dst)


def transfer_copy_preserve(src: PathLike, dst: str) -> None:
    """Copy a file from source to destination preserving metadata."""
    shutil.copy2(src, dst)


def transfer_move(src: PathLike, dst: str) -> None:
    """Move a file from source to destination."""
    shutil.move(src, dst)


def transfer_symlink(src: PathLike, dst: str) -> None:
    """Create a symlink from source to destination."""
    os.symlink(src, dst)


def transfer_hardlink(src: PathLike, dst: str) -> None:
    """Create a hardlink from source to destination.

    Falls back to symlink if hardlinking across filesystems fails.
    """
    try:
        os.link(src, dst)
    except OSError as e:
        if e.winerror == FileError.WINDOWS_CROSS_DRIVE_ERROR or e.errno == FileError.UNIX_CROSS_FILESYSTEM_ERROR:
            os.symlink(src, dst)
        else:
            raise
