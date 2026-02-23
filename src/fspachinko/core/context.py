"""Engine state classes."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from os.path import dirname
from typing import TYPE_CHECKING

from .constants import DateTimeFormat, StateStatus
from .helpers import remove_directory

if TYPE_CHECKING:
    from collections.abc import Callable

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
    is_create_unique_dirs: bool

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
        if not self.is_create_unique_dirs:
            self.locked_file.clear()

    def update(self, entry: FSEntry) -> None:
        """Update the quota state after processing a file."""
        parent = dirname(entry.path)
        self._dircount[parent] += 1
        if self._dircount[parent] >= self.max_per_dir:
            self.locked_dir.add(parent)

    def is_file_locked(self, entry: FSEntry) -> bool:
        """Check if a file is locked by the uniqueness rule."""
        return entry.path in self.locked_file

    def is_dir_locked_from_file(self, entry: FSEntry) -> bool:
        """Check if a directory is locked by the diversity rule."""
        return dirname(entry.path) in self.locked_dir

    def lock_file(self, entry: FSEntry) -> None:
        """Lock a file by adding it to the locked_file set."""
        self.locked_file.add(entry.path)


@dataclass(slots=True)
class Event:
    """Class for engine events."""


@dataclass(slots=True)
class ProcessFinished(Event):
    """Class for process finished state."""

    status: str = ""
    msg: str = ""


@dataclass(slots=True)
class Context:
    """Class for engine state context."""

    root: str
    is_create_folder: bool
    state: ProcessFinished = field(default_factory=ProcessFinished)
    is_stop_requested: bool = field(default=False)

    def _check(self, request: JobRequest, quota: DiversityQuota, gen_fn: Callable) -> bool:
        """Check and update state before file validation."""
        result = gen_fn(request, quota)
        if result is not None:
            self.state = result
            return True
        return False

    def should_stop(self, request: JobRequest, quota: DiversityQuota) -> bool:
        """Check and update state before file validation."""
        return self._check(request, quota, self.gen_stop_statemsg)

    def is_none_found(self, request: JobRequest, quota: DiversityQuota) -> bool:
        """Check if no files were found in the current folder."""
        return self._check(request, quota, self.gen_none_statemsg)

    def gen_stop_statemsg(self, request: JobRequest, quota: DiversityQuota) -> Event | None:
        """Generate state and message for reporting."""
        if request.file_count == request.target:
            return ProcessFinished(
                status=StateStatus.SUCCESS,
                msg="Transferred all requested files.",
            )

        if self.is_stop_requested:
            return ProcessFinished(
                status=StateStatus.USER_STOPPED,
                msg="Stopped by user.",
            )

        if self.root in quota.locked_dir:
            return ProcessFinished(
                status=StateStatus.ALL_FILES_SEARCHED,
                msg="Locked all files by diversity quota.",
            )

        return None

    def gen_none_statemsg(self, request: JobRequest, quota: DiversityQuota) -> Event | None:
        """Generate state and message for no files found scenario."""
        none_found = request.file_count == 0 and self.is_create_folder

        if none_found and self.root in quota.locked_dir:
            return ProcessFinished(
                status=StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED,
                msg="Found no valid files in root and locked all files by diversity quota.",
            )

        if none_found:
            return ProcessFinished(
                status=StateStatus.NO_FILES_FOUND_FOLDER_DELETED,
                msg="Found no valid files in root.",
            )

        return None

    def finalize(self, request: JobRequest, quota: DiversityQuota) -> None:
        """Finalize the context after processing."""
        if self.is_none_found(request, quota):
            remove_directory(request.dest)

    def generate_summary(self, request: JobRequest, timestamp: str) -> str:
        """Generate the summary report."""
        if self.state is None:
            return ""

        return (
            f"SUMMARY:\n"
            f"{self.state.msg}\n"
            f"{self.state.status}: {request.file_count}/{request.target} files transferred\n"
            "------------------------------------------------------------------------\n"
            f"Timestamp:    {timestamp}\n"
            f"Root:         {self.root}\n"
            f"Destination:  {request.dest}\n"
            f"Size:         {request.size_str}\n"
            f"Runtime:      {request.runtime_str}\n"
            "========================================================================\n"
        )
