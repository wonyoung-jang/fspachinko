"""File transfer strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from os import link, symlink
from shutil import copy, copy2, move

from ..constants import FileError


class AbstractTransfer(ABC):
    """Abstract base class for file transfer strategies."""

    @abstractmethod
    def transfer(self, src: str, dst: str) -> None:
        """Perform the file transfer operation."""


@dataclass(slots=True)
class DryRunTransfer(AbstractTransfer):
    """Represents a dry-run file transfer operation."""

    def transfer(self, src: str, dst: str) -> None:
        """Do nothing (dry-run)."""


@dataclass(slots=True)
class CopyTransfer(AbstractTransfer):
    """Represents a copy file transfer operation."""

    def transfer(self, src: str, dst: str) -> None:
        """Copy the file from source to destination."""
        copy(src, dst)


@dataclass(slots=True)
class CopyPreserveTransfer(AbstractTransfer):
    """Represents a copy with metadata preservation file transfer operation."""

    def transfer(self, src: str, dst: str) -> None:
        """Copy the file from source to destination while preserving metadata."""
        copy2(src, dst)


@dataclass(slots=True)
class MoveTransfer(AbstractTransfer):
    """Represents a move file transfer operation."""

    def transfer(self, src: str, dst: str) -> None:
        """Move the file from source to destination."""
        move(src, dst)


@dataclass(slots=True)
class SymlinkTransfer(AbstractTransfer):
    """Represents a symbolic link file transfer operation."""

    def transfer(self, src: str, dst: str) -> None:
        """Create a symbolic link from source to destination."""
        symlink(src, dst)


@dataclass(slots=True)
class HardlinkTransfer(AbstractTransfer):
    """Represents a hard link file transfer operation."""

    def transfer(self, src: str, dst: str) -> None:
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
