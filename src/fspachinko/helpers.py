"""Utility functions."""

from .constants import BytesIn, ByteUnit, StateStatus


def convert_byte_to_human_readable_size(nbytes: int) -> str:
    """Convert bytes to human readable string."""
    if nbytes < BytesIn.KILOBYTE:
        return f"{nbytes} {ByteUnit.BYTES}"

    conversion = {
        BytesIn.KILOBYTE: ByteUnit.KILOBYTES,
        BytesIn.MEGABYTE: ByteUnit.MEGABYTES,
        BytesIn.GIGABYTE: ByteUnit.GIGABYTES,
    }

    for threshold, unit in conversion.items():
        if nbytes < threshold * 1024:
            return f"{nbytes / threshold:.2f} {unit}"

    return f"{nbytes / BytesIn.GIGABYTE:.2f} {ByteUnit.GIGABYTES}"


def get_status(
    *, is_success: bool, is_none_found_and_create_dir: bool, is_stop_requested: bool, is_root_locked: bool
) -> str | StateStatus:
    """Get the state and message for reporting."""
    if is_success:
        return StateStatus.SUCCESS
    if is_stop_requested:
        return StateStatus.USER_STOPPED
    if is_none_found_and_create_dir and is_root_locked:
        return StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED
    if is_none_found_and_create_dir:
        return StateStatus.NO_FILES_FOUND_FOLDER_DELETED
    if is_root_locked:
        return StateStatus.ALL_FILES_SEARCHED
    return StateStatus.UNDEFINED


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
