"""Engine state classes."""

import logging
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from ..utils import DateTimeStamp, StateStatus, convert_byte_to_human_readable_size, remove_directory

if TYPE_CHECKING:
    from ..config import Folder, SizeLimit
    from .destination import JobRequest
    from .quota import DiversityQuota
    from .reporter import ReportWriter
    from .walker import FSEntry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DirectoryStatistic:
    """Dataclass for state."""

    count: int = 0
    starttime: float = 0.0
    curr_size: int = 0
    total_size: int = 0

    def reset(self) -> None:
        """Reset state variables for a new folder."""
        self.count = 0
        self.curr_size = 0
        self.starttime = perf_counter()

    def update(self, size: int) -> None:
        """Update state on successful operation."""
        self.count += 1
        self.curr_size += size
        self.total_size += size

    @property
    def runtime_str(self) -> str:
        """Get the runtime as a formatted string."""
        return f"{perf_counter() - self.starttime:.2f}s"

    @property
    def size_str(self) -> str:
        """Get the current size as a human-readable string."""
        return convert_byte_to_human_readable_size(self.curr_size)


@dataclass(slots=True)
class EngineContext:
    """Class for engine state context."""

    root: str
    folder: Folder
    quota: DiversityQuota
    folder_size_limit: SizeLimit
    total_size_limit: SizeLimit
    reporter: ReportWriter
    is_dry_run: bool
    dtstamp: DateTimeStamp
    state: str = ""
    msg: str = ""
    is_stop_requested: bool = False
    dirstat: DirectoryStatistic = field(default_factory=DirectoryStatistic)

    def should_stop(self, target: int) -> bool:
        """Check and update state before file validation."""
        if self.is_stop_requested:
            self.state = StateStatus.USER_STOPPED
            self.msg = "Stopped by user request"
        elif self.dirstat.count == target:
            self.state = StateStatus.SUCCESS
            self.msg = f"Copied {self.dirstat.count}/{target} files"
        elif self.root in self.quota.locked_dir:
            self.state = StateStatus.ALL_FILES_SEARCHED
            self.msg = "All files locked by diversity quota"
        elif self.folder_size_limit.is_valid(self.dirstat.curr_size):
            self.state = StateStatus.FOLDER_SIZE_LIMIT_REACHED
            self.msg = self.folder_size_limit.get_percent_str(self.dirstat.curr_size)
        elif self.total_size_limit.is_valid(self.dirstat.total_size):
            self.state = StateStatus.TOTAL_SIZE_LIMIT_REACHED
            self.msg = self.total_size_limit.get_percent_str(self.dirstat.total_size)
        else:
            return False
        return True

    def is_none_found(self) -> bool:
        """Check if no files were found in the current folder."""
        none_found = self.dirstat.count == 0 and self.folder.is_enabled
        if none_found and self.root in self.quota.locked_dir:
            self.state = StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED
            self.msg = "No files found and all files locked by diversity quota"
        elif none_found:
            self.state = StateStatus.NO_FILES_FOUND_FOLDER_DELETED
            self.msg = "No files found in the folder"
        else:
            return False
        return True

    def prepare(self, dest: str) -> None:
        """Prepare the context for a new folder processing."""
        self.dtstamp.reset()
        self.dirstat.reset()
        self.quota.reset()
        self.reporter.reset(dest)

    def update(self, entry: FSEntry) -> None:
        """Update context on successful file operation."""
        self.dirstat.update(entry.size)
        self.quota.update(entry)

    def finalize(self, request: JobRequest) -> str:
        """Finalize the context after processing."""
        none_found = self.is_none_found()
        report = self.reporter.generate_report(
            status=f"{self.state}: {self.dirstat.count}/{request.target} files copied",
            runtime=self.dirstat.runtime_str,
            size=self.dirstat.size_str,
        )
        self.reporter.save()

        if none_found:
            remove_directory(request.dest)

        return report
