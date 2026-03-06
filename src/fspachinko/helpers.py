"""Utility functions."""

import logging

from .constants import BytesIn, ByteUnit, StateStatus

logger = logging.getLogger(__name__)


def convert_byte_to_human_readable_size(nbytes: int) -> str:
    """Convert bytes to human readable string."""
    conversion: dict[BytesIn, str] = {
        BytesIn.KILOBYTE: f"{nbytes / BytesIn.BYTE:.2f} {ByteUnit.BYTES}",
        BytesIn.MEGABYTE: f"{nbytes / BytesIn.KILOBYTE:.2f} {ByteUnit.KILOBYTES}",
        BytesIn.GIGABYTE: f"{nbytes / BytesIn.MEGABYTE:.2f} {ByteUnit.MEGABYTES}",
    }
    for threshold, r_str in conversion.items():
        if nbytes < threshold:
            return r_str
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


def get_report(path: str, size_str: str, runtime_str: str, count: int, target_qty: int) -> str:
    """Generate a summary report string."""
    return (
        "------------------------------------------------------------------------\n"
        f"{count}/{target_qty} files transferred\n"
        "------------------------------------------------------------------------\n"
        f"Destination:  {path}\n"
        f"Size:         {size_str}\n"
        f"Runtime:      {runtime_str}\n"
        "========================================================================\n"
    )
