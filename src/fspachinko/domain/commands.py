"""Commands."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fspachinko.configuration.model import ConfigModel


@dataclass(frozen=True)
class Command:
    """Base class for commands."""


@dataclass(slots=True, frozen=True)
class RunTransferJob(Command):
    """Command to run the transfer job."""


@dataclass(slots=True, frozen=True)
class CreateTransferJob(Command):
    """Command to create a transfer job."""

    root: str
    max_per_dir: int | float
    unique_files_only: bool


@dataclass(slots=True, frozen=True)
class ProcessDirectory(Command):
    """Command to process a single directory (triggers a UoW transaction)."""

    dest_dir: str
    target_qty: int


@dataclass(slots=True, frozen=True)
class StopProcess(Command):
    """Command to stop the file transfer process."""


@dataclass(slots=True, frozen=True)
class SaveConfiguration(Command):
    """Command to save a configuration."""

    path: str
    config: dict


@dataclass(slots=True, frozen=True)
class LoadConfiguration(Command):
    """Command to load a configuration."""

    path: str


@dataclass(slots=True, frozen=True)
class BootstrapConfig(Command):
    """Command to bootstrap the configuration."""

    config: ConfigModel
