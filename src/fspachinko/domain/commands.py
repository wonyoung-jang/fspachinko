"""Commands."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Command:
    """Base class for commands."""


@dataclass(slots=True, frozen=True)
class StartProcess(Command):
    """Command to start the file transfer process."""


@dataclass(slots=True, frozen=True)
class StopProcess(Command):
    """Command to stop the file transfer process."""


@dataclass(slots=True, frozen=True)
class CreateFilenamer(Command):
    """Command to create a filenamer instance."""

    is_enabled: bool
    template: str
