"""File transfer strategies."""

from io import UnsupportedOperation
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ..utils import FileError, TransferMode

if TYPE_CHECKING:
    from collections.abc import Callable


def get_available_transfer_modes() -> tuple[TransferMode, ...]:
    """Detect which transfer modes are supported on the current OS."""
    available = []

    # COPY is always available
    available.append(TransferMode.COPY)

    # MOVE is always available
    available.append(TransferMode.MOVE)

    # SYMLINK availability
    try:
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_src = tmp_path / "test_src"
            test_dst = tmp_path / "test_symlink"
            test_src.touch()
            test_dst.symlink_to(test_src)
            test_dst.unlink()
            test_src.unlink()
        available.append(TransferMode.SYMLINK)
    except (OSError, UnsupportedOperation, NotImplementedError):
        pass

    # HARDLINK availability
    try:
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_src = tmp_path / "test_src"
            test_dst = tmp_path / "test_hardlink"
            test_src.touch()
            test_dst.hardlink_to(test_src)
            test_dst.unlink()
            test_src.unlink()
        available.append(TransferMode.HARDLINK)
    except (OSError, UnsupportedOperation, NotImplementedError):
        pass

    return tuple(available)


def fetch_transfer_strategy(mode: TransferMode) -> Callable:
    """Return the appropriate transfer strategy instance.

    Falls back to SYMLINK if the requested mode is not available.
    """
    strategy_map = {
        TransferMode.COPY: transfer_copy,
        TransferMode.MOVE: transfer_move,
        TransferMode.SYMLINK: transfer_symlink,
        TransferMode.HARDLINK: transfer_hardlink,
    }
    available_modes = get_available_transfer_modes()
    requested_mode = TransferMode(mode)
    if requested_mode in available_modes:
        return strategy_map[requested_mode]
    return transfer_symlink


def transfer_copy(src: Path, dst: Path) -> None:
    """Copy a file from source to destination."""
    src.copy(dst, preserve_metadata=True)


def transfer_move(src: Path, dst: Path) -> None:
    """Move a file from source to destination."""
    src.move(dst)


def transfer_symlink(src: Path, dst: Path) -> None:
    """Create a symlink from source to destination."""
    dst.symlink_to(src)


def transfer_hardlink(src: Path, dst: Path) -> None:
    """Create a hardlink from source to destination.

    Falls back to symlink if hardlinking across filesystems fails.
    """
    try:
        dst.hardlink_to(src)
    except OSError as e:
        if e.winerror == FileError.WINDOWS_CROSS_DRIVE_ERROR or e.errno == FileError.UNIX_CROSS_FILESYSTEM_ERROR:
            dst.symlink_to(src)
        else:
            raise
