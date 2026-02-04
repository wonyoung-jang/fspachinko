"""Engine state classes."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from ..utils import DateTimeStamp, StateStatus, remove_directory

if TYPE_CHECKING:
    import os

    from ..config import Folder, SizeLimit
    from .quota import DiversityQuota
    from .reporter import ReportWriter

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FolderStats:
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
class Context(ABC):
    """Abstract base class for engine state context."""

    folder: Folder
    quota: DiversityQuota
    folder_size_limit: SizeLimit
    total_size_limit: SizeLimit
    reporter: ReportWriter
    is_dry_run: bool
    is_stop_requested: bool = False
    folderstats: FolderStats = field(default_factory=FolderStats)
    _state: EngineState | None = None

    @property
    def state(self) -> EngineState:
        """Get the current engine state."""
        if self._state is None:
            msg = "Engine state is not set."
            raise ValueError(msg)
        return self._state

    @state.setter
    def state(self, new_state: EngineState) -> None:
        """Set a new engine state."""
        self._state = new_state
        self._state.context = self

    @abstractmethod
    def should_stop(self, target: int) -> bool:
        """Check and update state before file validation."""

    @abstractmethod
    def is_none_found(self) -> bool:
        """Check if no files were found in the current folder."""

    @abstractmethod
    def prepare(self, dest: str) -> None:
        """Prepare the context for a new folder processing."""

    @abstractmethod
    def update_on_success(self, entry: os.DirEntry) -> None:
        """Update context on successful file operation."""

    @abstractmethod
    def should_treat_as_dry_run(self, copy_path_str: str) -> bool:
        """Check if a file has already been transferred."""

    @abstractmethod
    def set_errored(self, copy_path_str: str) -> None:
        """Set the state to invalid file transfer."""

    @abstractmethod
    def set_transferred(self, copy_path_str: str) -> None:
        """Set the state to successful file transfer."""

    @abstractmethod
    def finalize(self, target: int, dest: str) -> str:
        """Finalize the context after processing."""


@dataclass(slots=True)
class EngineContext(Context):
    """Class for engine state context."""

    def should_stop(self, target: int) -> bool:
        """Check and update state before file validation."""
        if self.is_stop_requested:
            self.state = UserStoppedState(
                status=StateStatus.USER_STOPPED,
                message="Stopped by user request",
            )
            return True

        if self.folderstats.count == target:
            self.state = SuccessState(
                status=StateStatus.SUCCESS,
                message=f"Copied {self.folderstats.count}/{target} files",
            )
            return True

        if self.quota.is_all_locked():
            self.state = AllSearched(
                status=StateStatus.ALL_FILES_SEARCHED,
                message="All files locked by diversity quota",
            )
            return True

        if (
            self.folder_size_limit.is_enabled
            and self.folder_size_limit.size_limit > 0
            and self.folder_size_limit.is_valid(self.folderstats.curr_size)
        ):
            self.state = FolderSizeLimitState(
                status=StateStatus.FOLDER_SIZE_LIMIT_REACHED,
                message=f"{(self.folderstats.curr_size)} B / {(self.folder_size_limit.size_limit)} B",
            )
            return True

        if (
            self.total_size_limit.is_enabled
            and self.total_size_limit.size_limit > 0
            and self.total_size_limit.is_valid(self.folderstats.total_size)
        ):
            self.state = TotalSizeLimitState(
                status=StateStatus.TOTAL_SIZE_LIMIT_REACHED,
                message=f"{(self.folderstats.total_size)} B / {(self.total_size_limit.size_limit)} B",
            )
            return True

        return False

    def is_none_found(self) -> bool:
        """Check if no files were found in the current folder."""
        none_found = self.folderstats.count == 0 and self.folder.is_enabled
        if none_found:
            if self.quota.is_all_locked():
                self.state = NoFilesFoundAllSearchedState(
                    status=StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED,
                    message="No files found and all files locked by diversity quota",
                )
                return True

            self.state = NoFilesFoundState(
                status=StateStatus.NO_FILES_FOUND_FOLDER_DELETED,
                message="No files found in the folder",
            )
            return True

        return False

    def prepare(self, dest: str) -> None:
        """Prepare the context for a new folder processing."""
        DateTimeStamp.refresh()
        self.folderstats.reset()
        self.quota.reset()
        self.reporter.reset(dest)

    def update_on_success(self, entry: os.DirEntry) -> None:
        """Update context on successful file operation."""
        self.folderstats.update(entry.stat().st_size)
        self.quota.register_success(entry)

    def should_treat_as_dry_run(self, copy_path_str: str) -> bool:
        """Check if a file has already been transferred."""
        if self.is_dry_run:
            self.state = DryRunState(message=f"DRY - {copy_path_str}")
            return True
        return False

    def set_errored(self, copy_path_str: str) -> None:
        """Set the state to invalid file transfer."""
        self.state = TransferErrorState(message=f"FAILED - {copy_path_str}")

    def set_transferred(self, copy_path_str: str) -> None:
        """Set the state to successful file transfer."""
        self.state = TransferSuccessState(message=copy_path_str)

    def finalize(self, target: int, dest: str) -> str:
        """Finalize the context after processing."""
        none_found = self.is_none_found()
        report = self.reporter.generate_report(
            status=f"{self.state.status}: {self.folderstats.count}/{target} files copied",
            runtime=round(perf_counter() - self.folderstats.starttime, 2),
            size=self.folderstats.curr_size,
        )
        self.reporter.save()

        if none_found:
            remove_directory(dest)

        return report


@dataclass(slots=True)
class EngineState:
    """Abstract base class for engine states."""

    status: str = ""
    message: str = ""
    _context: Context | None = None

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        logger.debug("Change state to: %s", self.__class__.__name__)

    @property
    def context(self) -> Context:
        """Get the engine state context."""
        if self._context is None:
            msg = "Engine state context is not set."
            raise ValueError(msg)
        return self._context

    @context.setter
    def context(self, new_context: Context) -> None:
        """Set a new engine state context."""
        self._context = new_context


@dataclass(slots=True)
class RunningState(EngineState):
    """State representing engine running."""


@dataclass(slots=True)
class DryRunState(RunningState):
    """State representing engine running in dry-run mode."""


@dataclass(slots=True)
class TransferSuccessState(RunningState):
    """State representing successful file transfer."""


@dataclass(slots=True)
class TransferErrorState(RunningState):
    """State representing failed file transfer."""


@dataclass(slots=True)
class StoppedState(EngineState):
    """State representing engine stopped due to an error."""


@dataclass(slots=True)
class SuccessState(StoppedState):
    """State representing successful completion of folder processing."""


@dataclass(slots=True)
class UserStoppedState(StoppedState):
    """State representing user-requested stop of processing."""


@dataclass(slots=True)
class NoFilesFoundAllSearchedState(StoppedState):
    """State representing no files found in the folder and all files searched."""


@dataclass(slots=True)
class NoFilesFoundState(StoppedState):
    """State representing no files found in the folder."""


@dataclass(slots=True)
class AllSearched(StoppedState):
    """State representing all folders being searched."""


@dataclass(slots=True)
class FolderSizeLimitState(StoppedState):
    """State representing folder size limit reached."""


@dataclass(slots=True)
class TotalSizeLimitState(StoppedState):
    """State representing total size limit reached."""
