"""File transfer strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import UnsupportedOperation
from pathlib import Path
from tempfile import TemporaryDirectory

from ..utils.constants import FileError, TransferMode


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


def fetch_transfer_strategy(mode: TransferMode) -> Transfer:
    """Return the appropriate transfer strategy instance.

    Falls back to SYMLINK if the requested mode is not available.
    """
    strategy_map = {
        TransferMode.COPY: Copy,
        TransferMode.MOVE: Move,
        TransferMode.SYMLINK: Symlink,
        TransferMode.HARDLINK: Hardlink,
    }
    available_modes = get_available_transfer_modes()
    requested_mode = TransferMode(mode)
    if requested_mode in available_modes:
        return strategy_map[requested_mode]()
    return Symlink()


@dataclass(slots=True)
class Transfer(ABC):
    """Dataclass for transfer strategy.

    Note: Only modes returned by get_available_transfer_modes() should be used.
    """

    @abstractmethod
    def transfer(self, src: Path, dst: Path) -> None:
        """Perform the transfer from source to destination."""


@dataclass(slots=True)
class Copy(Transfer):
    """Dataclass for copy strategy."""

    def transfer(self, src: Path, dst: Path) -> None:
        """Perform the copy from source to destination."""
        src.copy(dst, preserve_metadata=True)


@dataclass(slots=True)
class Move(Transfer):
    """Dataclass for move strategy."""

    def transfer(self, src: Path, dst: Path) -> None:
        """Perform the move from source to destination."""
        src.move(dst)


@dataclass(slots=True)
class Symlink(Transfer):
    """Dataclass for symlink strategy."""

    def transfer(self, src: Path, dst: Path) -> None:
        """Perform the symlink from source to destination."""
        dst.symlink_to(src)


@dataclass(slots=True)
class Hardlink(Transfer):
    """Dataclass for hardlink strategy."""

    def transfer(self, src: Path, dst: Path) -> None:
        """Perform the hardlink from source to destination.

        Falls back to symlink if hardlinking across filesystems fails.
        """
        try:
            dst.hardlink_to(src)
        except OSError as e:
            if e.winerror == FileError.WINDOWS_CROSS_DRIVE_ERROR or e.errno == FileError.UNIX_CROSS_FILESYSTEM_ERROR:
                dst.symlink_to(src)
            else:
                raise
