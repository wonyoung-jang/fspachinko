"""Utility functions."""

from dataclasses import dataclass

from fspachinko.constants import SIZE_MAP, StateStatus


def dest_path_str(path: str) -> str:
    """Get the destination path string."""
    return f"Destination: {path}"


def count_ratio_str(count: int, target: int) -> str:
    """Get the count/target ratio string."""
    return f"{count}/{target} ({count / target:.2%}) files transferred"


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
        f"{count_ratio_str(count, target)}\n"
        "------------------------------------------------------------------------\n"
        f"{dest_path_str(path)}\n"
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

    path: str
    size: int
    count: int
    target_qty: int
    is_success: bool
    is_empty_creation: bool
    is_stop_requested: bool
    is_root_locked: bool
    _report: str = ""
    _status: str = ""

    def __post_init__(self) -> None:
        """Generate the report string after initialization."""
        self._status = get_status(
            success=self.is_success,
            stop_requested=self.is_stop_requested,
            empty_creation=self.is_empty_creation,
            root_locked=self.is_root_locked,
        )
        self._report = get_report(
            path=self.path,
            size=self.size,
            count=self.count,
            target=self.target_qty,
        )

    def __str__(self) -> str:
        """Get the full report string."""
        return f"\n\n{self._status}\n{self._report}\n"
