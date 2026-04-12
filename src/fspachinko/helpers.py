"""Utility functions."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fspachinko.constants import SIZE_MAP, StateStatus

if TYPE_CHECKING:
    from fspachinko.domain.events import DirectoryTransferred


def filesize_str(nbytes: int) -> str:
    """Convert bytes to human readable string."""
    for unit, threshold in SIZE_MAP.items():
        if nbytes < threshold * 1024:
            result = f"Size: {nbytes / threshold:.2f} {unit}"
            break
    return result


def get_report(path: str, size: int, count: int, target: int) -> str:
    """Generate a summary report string."""
    return (
        "------------------------------------------------------------------------\n"
        f"{count}/{target} ({count / target:.2%}) files transferred\n"
        "------------------------------------------------------------------------\n"
        f"Destination: {path}\n"
        f"{filesize_str(size)}\n"
        "========================================================================\n"
    )


def get_status(
    *,
    success: bool,
    stop_requested: bool,
    empty_creation: bool,
    root_locked: bool,
) -> str:
    """Get the state and message for reporting."""
    if success:
        return StateStatus.SUCCESS
    if stop_requested:
        return StateStatus.USER_STOPPED
    match empty_creation, root_locked:
        case True, True:
            return StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED
        case True, False:
            return StateStatus.NO_FILES_FOUND_FOLDER_DELETED
        case False, True:
            return StateStatus.ALL_FILES_SEARCHED
    return StateStatus.UNDEFINED


@dataclass(slots=True)
class ReportWriter:
    """Helper class to write report."""

    evt: DirectoryTransferred
    _report_str: str = ""

    def __post_init__(self) -> None:
        """Generate the report string after initialization."""
        _status = get_status(
            success=self.evt.is_success,
            stop_requested=self.evt.is_stop_requested,
            empty_creation=self.evt.is_empty_creation,
            root_locked=self.evt.is_root_locked,
        )
        _report = get_report(
            path=self.evt.path,
            size=self.evt.size,
            count=self.evt.count,
            target=self.evt.target_qty,
        )
        self._report_str = f"\n\n{_status}\n{_report}\n"

    def __str__(self) -> str:
        """Get the full report string."""
        return self._report_str
