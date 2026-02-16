"""Engine state classes."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from os.path import dirname
from time import perf_counter
from typing import TYPE_CHECKING

from .constants import DateTimeFormat, StateStatus
from .helpers import convert_byte_to_human_readable_size, remove_directory

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .engine import JobRequest
    from .walker import FSEntry


@dataclass(slots=True)
class DateTimeStamp:
    """Provider for current date and time."""

    date: str = field(init=False)
    time: str = field(init=False)
    date_time: str = field(init=False)
    date_time_report_str: str = field(init=False)

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        self.reset()

    def reset(self) -> None:
        """Refresh the current date and time."""
        now = datetime.now(tz=UTC)
        self.date = now.strftime(DateTimeFormat.DATE)
        self.time = now.strftime(DateTimeFormat.TIME)
        self.date_time = f"{self.date}--{self.time}"
        self.date_time_report_str = now.strftime(DateTimeFormat.DATETIME)


@dataclass(slots=True)
class DiversityQuota:
    """Manages rules for diversity (weights) and uniqueness."""

    max_per_dir: int | float
    is_create_unique_folders: bool

    locked_dir: set[str] = field(default_factory=set)
    locked_file: set[str] = field(default_factory=set)
    _dircount: Counter[str] = field(default_factory=Counter)

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        if self.max_per_dir <= 0:
            self.max_per_dir = float("inf")

    def reset(self) -> None:
        """Reset the quota state for a new folder."""
        self._dircount.clear()
        self.locked_dir.clear()
        if not self.is_create_unique_folders:
            self.locked_file.clear()

    def update(self, entry: FSEntry) -> None:
        """Update the quota state after processing a file."""
        parent = dirname(entry.path)
        self._dircount[parent] += 1
        if self._dircount[parent] >= self.max_per_dir:
            self.locked_dir.add(parent)


@dataclass(slots=True)
class OutputTotalStat:
    """Dataclass for a single output directory statistics."""

    total_size: int = 0
    total_file_count: int = 0
    start_time: float = 0.0


@dataclass(slots=True)
class OutputDirStat:
    """Dataclass for a single output directory statistics."""

    file_count: int = 0
    curr_size: int = 0
    start_time: float = 0.0
    total_size: int = 0

    def reset(self) -> None:
        """Reset state variables for a new folder."""
        self.file_count = 0
        self.curr_size = 0
        self.start_time = perf_counter()

    def update(self, size: int) -> None:
        """Update state on successful operation."""
        self.file_count += 1
        self.curr_size += size
        self.total_size += size

    @property
    def runtime_str(self) -> str:
        """Get the runtime as a formatted string."""
        return f"{perf_counter() - self.start_time:.2f}s"

    @property
    def size_str(self) -> str:
        """Get the current size as a human-readable string."""
        return convert_byte_to_human_readable_size(self.curr_size)


@dataclass(slots=True)
class StaticEngineContext:
    """Static context for the engine."""

    root: str
    dest: str
    is_dry_run: bool
    is_create_folder: bool
    should_follow_symlink: bool


@dataclass(slots=True)
class EngineContext:
    """Class for engine state context."""

    root: str
    is_create_folder: bool
    is_dry_run: bool
    quota: DiversityQuota
    dtstamp: DateTimeStamp

    state: str = field(default="")
    msg: str = field(default="")
    is_stop_requested: bool = field(default=False)
    dir_stat: OutputDirStat = field(default_factory=OutputDirStat)
    total_stat: OutputTotalStat = field(default_factory=OutputTotalStat)

    def should_stop(self, target: int) -> bool:
        """Check and update state before file validation."""
        self.state, self.msg = next(self.generate_state_msg(target), ("", ""))
        return bool(self.state and self.msg)

    def generate_state_msg(self, target: int) -> Iterator[tuple[str, str]]:
        """Generate state and message for reporting."""
        dir_stat = self.dir_stat
        if self.is_stop_requested:
            yield StateStatus.USER_STOPPED, "Stopped by user request"
        elif dir_stat.file_count == target:
            yield StateStatus.SUCCESS, f"Transferred {dir_stat.file_count}/{target} files"
        elif self.root in self.quota.locked_dir:
            yield StateStatus.ALL_FILES_SEARCHED, "All files locked by diversity quota"

    def is_none_found(self) -> bool:
        """Check if no files were found in the current folder."""
        state, msg = next(self.generate_none_found_state_msg(), ("", ""))
        if state and msg:
            self.state, self.msg = state, msg
            return True
        return False

    def generate_none_found_state_msg(self) -> Iterator[tuple[str, str]]:
        """Generate state and message for no files found scenario."""
        none_found = self.dir_stat.file_count == 0 and self.is_create_folder
        if none_found and self.root in self.quota.locked_dir:
            yield (
                StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED,
                "No files found and all files locked by diversity quota",
            )
        elif none_found:
            yield StateStatus.NO_FILES_FOUND_FOLDER_DELETED, "No files found in the folder"

    def prepare(self) -> None:
        """Prepare the context for a new folder processing."""
        self.dtstamp.reset()
        self.dir_stat.reset()
        self.quota.reset()

    def update(self, entry: FSEntry) -> None:
        """Update context on successful file operation."""
        self.dir_stat.update(entry.size)
        self.quota.update(entry)

    def finalize(self, request: JobRequest) -> None:
        """Finalize the context after processing."""
        if self.is_none_found():
            remove_directory(request.dest)

    def generate_report_header(self, request: JobRequest) -> str:
        """Generate the header report string."""
        return (
            f"{self.state}: {self.dir_stat.file_count}/{request.target} files copied"
            "\n------------------------------------------------------------------------\n"
            f"Timestamp:    {self.dtstamp.date_time_report_str}\n"
            f"Root:         {self.root}\n"
            f"Destination:  {request.dest}\n"
            f"Size:         {self.dir_stat.size_str}\n"
            f"Runtime:      {self.dir_stat.runtime_str}\n"
            f"Is Dry Run:   {self.is_dry_run}\n"
            "\n========================================================================\n"
        )
