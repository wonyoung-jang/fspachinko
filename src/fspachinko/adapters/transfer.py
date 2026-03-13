"""File transfer strategies."""

from io import UnsupportedOperation
from os import link, symlink, unlink
from os.path import join
from shutil import copy, copy2, move
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ..constants import FileError, TransferMode

if TYPE_CHECKING:
    from collections.abc import Callable


def get_available_transfer_modes() -> dict[TransferMode, Callable]:
    """Return the set of available transfer modes based on the current environment."""
    available = {
        TransferMode.DRY_RUN: lambda _, __: None,
        TransferMode.COPY: copy,
        TransferMode.COPY_PRESERVE: copy2,
        TransferMode.MOVE: move,
        TransferMode.SYMLINK: symlink,
        TransferMode.HARDLINK: hardlink,
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


def hardlink(src: str, dst: str) -> None:
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
