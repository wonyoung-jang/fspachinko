"""Utility functions."""

from fspachinko.constants import SIZE_MAP, StateStatus


def convert_byte_to_human_readable_size(nbytes: int, size_map: dict[str, int] = SIZE_MAP) -> str:
    """Convert bytes to human readable string."""
    for unit, threshold in size_map.items():
        if nbytes < threshold * 1024:
            result = f"{nbytes / threshold:.2f} {unit}"
            break
    return result


def get_status(
    *,
    success: bool,
    stop_requested: bool,
    empty_creation: bool,
    root_locked: bool,
    status: type[StateStatus] = StateStatus,
) -> str:
    """Get the state and message for reporting."""
    if success:
        return status.SUCCESS
    if stop_requested:
        return status.USER_STOPPED
    return {
        (True, True): status.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED,
        (True, False): status.NO_FILES_FOUND_FOLDER_DELETED,
        (False, True): status.ALL_FILES_SEARCHED,
    }.get((empty_creation, root_locked), status.UNDEFINED)


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
