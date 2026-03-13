"""Commands."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """Base class for commands."""


@dataclass(slots=True, frozen=True)
class StartProcessingDirectory(Command):
    """Command to process a single directory (triggers a UoW transaction)."""

    dest_dir: str
    target_qty: int


@dataclass(slots=True, frozen=True)
class StopProcess(Command):
    """Command to stop the file transfer process."""
