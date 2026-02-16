"""Engine state classes."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from os.path import dirname
from typing import TYPE_CHECKING

from .constants import DateTimeFormat, StateStatus
from .helpers import remove_directory

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

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

    def _check(self, request: JobRequest, gen_fn: Callable) -> bool:
        """Check and update state before file validation."""
        result = next(gen_fn(request), None)
        if result is not None:
            self.state, self.msg = result
            return True
        return False

    def should_stop(self, request: JobRequest) -> bool:
        """Check and update state before file validation."""
        return self._check(request, self.gen_stop_statemsg)

    def is_none_found(self, request: JobRequest) -> bool:
        """Check if no files were found in the current folder."""
        return self._check(request, self.gen_none_statemsg)

    def gen_stop_statemsg(self, request: JobRequest) -> Iterator[tuple[str, str]]:
        """Generate state and message for reporting."""
        if self.is_stop_requested:
            yield StateStatus.USER_STOPPED, "Stopped by user request"
        elif request.file_count == request.target:
            yield StateStatus.SUCCESS, f"Transferred {request.file_count}/{request.target} files"
        elif self.root in self.quota.locked_dir:
            yield StateStatus.ALL_FILES_SEARCHED, "All files locked by diversity quota"

    def gen_none_statemsg(self, request: JobRequest) -> Iterator[tuple[str, str]]:
        """Generate state and message for no files found scenario."""
        none_found = request.file_count == 0 and self.is_create_folder
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
        self.quota.reset()

    def update(self, entry: FSEntry) -> None:
        """Update context on successful file operation."""
        self.quota.update(entry)

    def finalize(self, request: JobRequest) -> None:
        """Finalize the context after processing."""
        if self.is_none_found(request):
            remove_directory(request.dest)

    def generate_report_header(self, request: JobRequest) -> str:
        """Generate the header report string."""
        r = request
        return (
            f"SUMMARY:\n"
            f"{self.msg}\n"
            f"{self.state}: {r.file_count}/{r.target} files transferred\n"
            "------------------------------------------------------------------------\n"
            f"Timestamp:    {self.dtstamp.date_time_report_str}\n"
            f"Root:         {self.root}\n"
            f"Destination:  {r.dest}\n"
            f"Size:         {r.size_str}\n"
            f"Runtime:      {r.runtime_str}\n"
            f"Is Dry Run:   {self.is_dry_run}\n"
            "========================================================================\n"
        )
