"""File transfer strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..utils.constants import TransferMode

if TYPE_CHECKING:
    from pathlib import Path


def fetch_transfer_strategy(mode: str) -> Transfer:
    """Return the appropriate transfer strategy instance."""
    return {
        TransferMode.COPY: Copy,
        TransferMode.MOVE: Move,
        TransferMode.SYMLINK: Symlink,
        TransferMode.HARDLINK: Hardlink,
    }.get(mode, Symlink)()


@dataclass(slots=True)
class Transfer(ABC):
    """Dataclass for transfer strategy."""

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
        """Perform the hardlink from source to destination."""
        dst.hardlink_to(src)
