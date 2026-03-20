"""Commands."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """Base class for commands."""


@dataclass(slots=True, frozen=True)
class CreateTransferJob(Command):
    """Command to create a transfer job."""

    root: str
    max_per_dir: int | float
    unique_files_only: bool


@dataclass(slots=True, frozen=True)
class ProcessDirectory(Command):
    """Command to process a single directory (triggers a UoW transaction)."""

    path: str
    target_qty: int


@dataclass(slots=True, frozen=True)
class StopProcess(Command):
    """Command to stop the file transfer process."""


@dataclass(slots=True, frozen=True)
class CreateTransferFn(Command):
    """Command to create a transfer function."""

    transfermode: str


@dataclass(slots=True, frozen=True)
class CreateFilenameFn(Command):
    """Command to create a filename function."""

    template: str
    is_enabled: bool


@dataclass(slots=True, frozen=True)
class CreateFilecountFn(Command):
    """Command to create a file count function."""

    count: int
    rand_range: tuple[int, int]
    is_rand_enabled: bool


@dataclass(slots=True, frozen=True)
class CreateDirnameFn(Command):
    """Command to create a directory name function."""

    dest: str
    name: str
    is_enabled: bool


@dataclass(slots=True, frozen=True)
class CreateWalkerFn(Command):
    """Command to create a walker function."""

    root: str
    should_follow_symlink: bool


@dataclass(slots=True, frozen=True)
class CreateTextFilterFn(Command):
    """Command to create a text filter function."""

    name: str
    text: str
    re_fmt: str
    is_enabled: bool
    should_include: bool


@dataclass(slots=True, frozen=True)
class CreateRangeFilterFn(Command):
    """Command to create a range filter function."""

    name: str
    minimum: int | float
    maximum: int | float
    is_enabled: bool


@dataclass(slots=True, frozen=True)
class CreateFilefilterFn(Command):
    """Command to create a file filter function."""
