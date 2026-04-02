"""Utility functions."""

from fspachinko.constants import SIZE_MAP, StateStatus


def convert_byte_to_human_readable_size(nbytes: int) -> str:
    """Convert bytes to human readable string."""
    for unit, threshold in SIZE_MAP.items():
        if nbytes < threshold * 1024:
            result = f"{nbytes / threshold:.2f} {unit}"
            break
    return result


def get_status(*, success: bool, stop_requested: bool, empty_creation: bool, root_locked: bool) -> str:
    """Get the state and message for reporting."""
    if success:
        return StateStatus.SUCCESS
    if stop_requested:
        return StateStatus.USER_STOPPED
    return {
        (True, True): StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED,
        (True, False): StateStatus.NO_FILES_FOUND_FOLDER_DELETED,
        (False, True): StateStatus.ALL_FILES_SEARCHED,
    }.get((empty_creation, root_locked), StateStatus.UNDEFINED)


def get_report(path: str, size: int, count: int, target_qty: int) -> str:
    """Generate a summary report string."""
    size_str = convert_byte_to_human_readable_size(size)
    return (
        "------------------------------------------------------------------------\n"
        f"{count}/{target_qty} files transferred\n"
        "------------------------------------------------------------------------\n"
        f"Destination:  {path}\n"
        f"Size:         {size_str}\n"
        "========================================================================\n"
    )
