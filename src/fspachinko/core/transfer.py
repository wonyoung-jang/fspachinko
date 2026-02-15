"""File transfer strategies."""

import os
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


def fetch_transfer_strategy(mode: str) -> Callable[[PathLike[str], str], None]:
    """Return the appropriate transfer strategy instance.

    Falls back to SYMLINK if the requested mode is not available.
    Falls back to COPY if SYMLINK is not available.
    """
    mapping: dict[TransferMode, Any] = {
        TransferMode.COPY: copy,
        TransferMode.COPY_PRESERVE: copy2,
        TransferMode.MOVE: move,
        TransferMode.SYMLINK: symlink,
        TransferMode.HARDLINK: hardlink,
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
