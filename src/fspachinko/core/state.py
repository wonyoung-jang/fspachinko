"""Engine state classes."""

import logging
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from ..utils import DateTimeStamp, StateStatus, remove_directory

if TYPE_CHECKING:
    from ..config import Folder, SizeLimit
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


@dataclass(slots=True)
class EngineContext:
    """Class for engine state context."""

    folder: Folder
    quota: DiversityQuota
    folder_size_limit: SizeLimit
    total_size_limit: SizeLimit
    reporter: ReportWriter
    is_dry_run: bool
    dtstamp: DateTimeStamp
    status: str = ""
    msg: str = ""
    is_stop_requested: bool = False
    dirstat: DirectoryStatistic = field(default_factory=DirectoryStatistic)

    def should_stop(self, target: int) -> bool:
        """Check and update state before file validation."""
        if self.is_stop_requested:
            self.status = StateStatus.USER_STOPPED
            self.msg = "Stopped by user request"
            return True

        if self.dirstat.count == target:
            self.status = StateStatus.SUCCESS
            self.msg = f"Copied {self.dirstat.count}/{target} files"
            return True

        if self.quota.is_all_locked():
            self.status = StateStatus.ALL_FILES_SEARCHED
            self.msg = "All files locked by diversity quota"
            return True

        if self.folder_size_limit.is_valid(self.dirstat.curr_size):
            self.status = StateStatus.FOLDER_SIZE_LIMIT_REACHED
            self.msg = f"{round(self.dirstat.curr_size * 100 / self.folder_size_limit.size_limit, 2)} %"
            return True

        if self.total_size_limit.is_valid(self.dirstat.total_size):
            self.status = StateStatus.TOTAL_SIZE_LIMIT_REACHED
            self.msg = f"{round(self.dirstat.total_size * 100 / self.total_size_limit.size_limit, 2)} %"
            return True

        return False

    def is_none_found(self) -> bool:
        """Check if no files were found in the current folder."""
        none_found = self.dirstat.count == 0 and self.folder.is_enabled
        if none_found:
            if self.quota.is_all_locked():
                self.status = StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED
                self.msg = "No files found and all files locked by diversity quota"
                return True

            self.status = StateStatus.NO_FILES_FOUND_FOLDER_DELETED
            self.msg = "No files found in the folder"
            return True

        return False

    def prepare(self, dest: str) -> None:
        """Prepare the context for a new folder processing."""
        self.dtstamp.reset()
        self.dirstat.reset()
        self.quota.reset()
        self.reporter.reset(dest)

    def update_on_success(self, entry: FSEntry) -> None:
        """Update context on successful file operation."""
        self.dirstat.update(entry.size)
        self.quota.register_success(entry)

    def finalize(self, target: int, dest: str) -> str:
        """Finalize the context after processing."""
        none_found = self.is_none_found()
        report = self.reporter.generate_report(
            status=f"{self.status}: {self.dirstat.count}/{target} files copied",
            runtime=round(perf_counter() - self.dirstat.starttime, 2),
            size=self.dirstat.curr_size,
        )
        self.reporter.save()

        if none_found:
            remove_directory(dest)

        return report
