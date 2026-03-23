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

    dest_dir: str
    target_qty: int


@dataclass(slots=True, frozen=True)
class StopProcess(Command):
    """Command to stop the file transfer process."""


@dataclass(slots=True, frozen=True)
class SetRngSeed(Command):
    """Command to set the RNG seed."""

    rng_seed: int | str | bytes | None


@dataclass(slots=True, frozen=True)
class SetPipelineCreateDir(Command):
    """Command to set the pipeline's create_dir flag."""

    is_create_dir: bool


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
class CreateDestDirs(Command):
    """Command to create destination directories."""

    dir_count: int
    directory_dest: str
    directory_name: str
    directory_create_is_enabled: bool
    filecount_static: int
    filecount_randrange: tuple[int, int]
    filecount_rand_is_enabled: bool


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


@dataclass(slots=True, frozen=True)
class SaveProfile(Command):
    """Command to save a profile."""

    path: str
    config: dict


@dataclass(slots=True, frozen=True)
class LoadProfile(Command):
    """Command to load a profile."""

    path: str
