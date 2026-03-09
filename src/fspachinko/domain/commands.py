"""Commands."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Command:
    """Base class for commands."""


@dataclass(slots=True, frozen=True)
class StartProcess(Command):
    """Command to start the file transfer process."""

    dir_count: int


@dataclass(slots=True, frozen=True)
class StopProcess(Command):
    """Command to stop the file transfer process."""


@dataclass(slots=True, frozen=True)
class ProcessDirectory(Command):
    """Command to process a single directory (triggers a UoW transaction)."""

    di: int
    target_qty: int
