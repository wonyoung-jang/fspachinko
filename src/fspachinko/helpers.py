"""Utility functions."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fspachinko.fp import Fp

if TYPE_CHECKING:
    from fspachinko.domain.events import DirectoryTransferred


def filesize_str(nbytes: int) -> str:
    """Convert bytes to human readable string."""
    for unit, threshold in Fp.SIZE_MAP.items():
        if nbytes >= threshold:
            return f"Size: {nbytes / threshold:.2f} {unit}"
    return f"Size: {nbytes} B"


@dataclass(slots=True, frozen=True)
class ReportSummary:
    """Helper class to represent the report summary."""

    path: str
    size: int
    count: int
    target: int

    def __str__(self) -> str:
        """Get the report summary as a string."""
        return (
            "------------------------------------------------------------------------\n"
            f"{self.count}/{self.target} ({self.count / self.target:.2%}) files transferred\n"
            "------------------------------------------------------------------------\n"
            f"Destination: {self.path}\n"
            f"{filesize_str(self.size)}\n"
            "========================================================================\n"
        )


@dataclass(slots=True, frozen=True)
class ReportStatus:
    """Helper class to represent the report status."""

    success: bool
    stop_requested: bool
    empty_creation: bool
    root_locked: bool

    def __str__(self) -> str:
        """Get the status as a string."""
        if self.success:
            return Fp.StateStatus.SUCCESS
        if self.stop_requested:
            return Fp.StateStatus.USER_STOPPED
        match self.empty_creation, self.root_locked:
            case True, True:
                return Fp.StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED
            case True, False:
                return Fp.StateStatus.NO_FILES_FOUND_FOLDER_DELETED
            case False, True:
                return Fp.StateStatus.ALL_FILES_SEARCHED
        return Fp.StateStatus.UNDEFINED


@dataclass(slots=True, frozen=True)
class ReportWriter:
    """Helper class to write report."""

    evt: DirectoryTransferred

    def __str__(self) -> str:
        """Get the full report string."""
        e = self.evt
        status = ReportStatus(e.is_success, e.is_stop_requested, e.is_empty_creation, e.is_root_locked)
        report = ReportSummary(e.path, e.size, e.count, e.target_qty)
        return f"\n\n{status}\n{report}\n"
