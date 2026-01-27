"""Engine state classes for MandalaEngine."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from mandala.config import Folder, SizeLimit

    from .quota import DiversityQuota

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FolderStats:
    """Dataclass for Mandala state."""

    count: int = 0
    starttime: float = 0.0
    curr_size: int = 0
    total_size: int = 0

    def reset_for_folder(self) -> None:
        """Reset state variables for a new folder."""
        self.count = 0
        self.curr_size = 0
        self.starttime = perf_counter()

    def update_folder(self, size: int) -> None:
        """Update state on successful operation."""
        self.count += 1
        self.curr_size += size
        self.total_size += size


@dataclass(slots=True)
class EngineStateContext(ABC):
    """Abstract base class for engine state context."""

    stop_requested: bool
    folder: Folder
    folderstats: FolderStats
    quota: DiversityQuota
    folder_size_limit: SizeLimit
    total_size_limit: SizeLimit
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
    def prepare(self) -> None:
        """Prepare the context for a new folder processing."""

    @abstractmethod
    def update_on_success(self, path: Path, size: int) -> None:
        """Update context on successful file operation."""


@dataclass(slots=True)
class MandalaEngineStateContext(EngineStateContext):
    """Abstract base class for engine state context."""

    def should_stop(self, target: int) -> bool:
        """Check and update state before file validation."""
        if self.stop_requested:
            self.state = UserStoppedState(
                status_prefix="USER STOPPED",
                message="Stopped by user request",
            )
            return True

        if self.folderstats.count >= target:
            self.state = SuccessState(
                status_prefix="SUCCESS",
                message=f"Copied {self.folderstats.count}/{target} files",
            )
            return True

        if self.quota.all_locked():
            self.state = AllSearched(
                status_prefix="ALL FILES SEARCHED",
                message="All files locked by diversity quota",
            )
            return True

        if self.folder_size_limit.is_exceeded(self.folderstats.curr_size):
            self.state = FolderSizeLimitState(
                status_prefix="FOLDER SIZE LIMIT REACHED",
                message=f"{(self.folderstats.curr_size)} B / {(self.folder_size_limit.size_limit)} B",
            )
            return True

        if self.total_size_limit.is_exceeded(self.folderstats.total_size):
            self.state = TotalSizeLimitState(
                status_prefix="TOTAL SIZE LIMIT REACHED",
                message=f"{(self.folderstats.total_size)} B / {(self.total_size_limit.size_limit)} B",
            )
            return True

        return False

    def is_none_found(self) -> bool:
        """Check if no files were found in the current folder."""
        none_found = self.folderstats.count == 0 and self.folder.create_enabled
        if none_found:
            if self.quota.all_locked():
                self.state = NoFilesFoundAllSearchedState(
                    status_prefix="NO FILES FOUND | ALL FILES SEARCHED | FOLDER DELETED",
                    message="No files found and all files locked by diversity quota",
                )
                return True

            self.state = NoFilesFoundState(
                status_prefix="NO FILES FOUND | FOLDER DELETED",
                message="No files found in the folder",
            )
            return True

        return False

    def prepare(self) -> None:
        """Prepare the context for a new folder processing."""
        self.folderstats.reset_for_folder()
        self.quota.prepare_for_batch()

    def update_on_success(self, path: Path, size: int) -> None:
        """Update context on successful file operation."""
        self.folderstats.update_folder(size)
        self.quota.register_success(path)


@dataclass(slots=True)
class EngineState:
    """Abstract base class for engine states."""

    status_prefix: str = ""
    message: str = ""
    _context: EngineStateContext | None = None

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        logger.info("Engine state changed to: %s", self.__class__.__name__)

    @property
    def context(self) -> EngineStateContext:
        """Get the engine state context."""
        if self._context is None:
            msg = "Engine state context is not set."
            raise ValueError(msg)
        return self._context

    @context.setter
    def context(self, new_context: EngineStateContext) -> None:
        """Set a new engine state context."""
        self._context = new_context


@dataclass(slots=True)
class SuccessState(EngineState):
    """State representing successful completion of folder processing."""


@dataclass(slots=True)
class UserStoppedState(EngineState):
    """State representing user-requested stop of processing."""


@dataclass(slots=True)
class NoFilesFoundAllSearchedState(EngineState):
    """State representing no files found in the folder and all files searched."""


@dataclass(slots=True)
class NoFilesFoundState(EngineState):
    """State representing no files found in the folder."""


@dataclass(slots=True)
class AllSearched(EngineState):
    """State representing all folders being searched."""


@dataclass(slots=True)
class FolderSizeLimitState(EngineState):
    """State representing folder size limit reached."""


@dataclass(slots=True)
class TotalSizeLimitState(EngineState):
    """State representing total size limit reached."""
