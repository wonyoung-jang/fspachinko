"""File transfer strategies."""

import os
from io import UnsupportedOperation
from os import PathLike, link, symlink, unlink
from shutil import copy, copy2, move
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ..utils import FileError, TransferMode

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
    except (OSError, UnsupportedOperation, NotImplementedError):
        pass

    # HARDLINK availability
    try:
        with TemporaryDirectory() as tmpdir:
            _test_link_creation(link)
        available.append(TransferMode.HARDLINK)
    except (OSError, UnsupportedOperation, NotImplementedError):
        pass

    return tuple(available)


def fetch_transfer_strategy(mode: str) -> Callable[[PathLike, str], None]:
    """Return the appropriate transfer strategy instance.

    Falls back to SYMLINK if the requested mode is not available.
    """
    strategy_map = {
        TransferMode.COPY: lambda src, dst: copy(src, dst),
        TransferMode.COPY_PRESERVE: lambda src, dst: copy2(src, dst),
        TransferMode.MOVE: lambda src, dst: move(src, dst),
        TransferMode.SYMLINK: lambda src, dst: symlink(src, dst),
        TransferMode.HARDLINK: transfer_hardlink,
    }
    available_modes = get_available_transfer_modes()
    requested_mode = TransferMode(mode)
    if requested_mode in available_modes:
        return strategy_map[requested_mode]
    return lambda src, dst: symlink(src, dst)


def transfer_hardlink(src: PathLike, dst: str) -> None:
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
