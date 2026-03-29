"""Utility functions."""

import re

from fspachinko.constants import SIZE_MAP, StateStatus


def convert_byte_to_human_readable_size(nbytes: int) -> str:
    """Convert bytes to human readable string."""
    for unit, threshold in SIZE_MAP.items():
        if nbytes < threshold * 1024:
            result = f"{nbytes / threshold:.2f} {unit}"
            break
    return result


def get_status(*, success: bool, empty_creation: bool, stop_requested: bool, root_locked: bool) -> str:
    """Get the state and message for reporting."""
    if success:
        return StateStatus.SUCCESS
    if stop_requested:
        return StateStatus.USER_STOPPED
    if empty_creation and root_locked:
        return StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED
    if empty_creation:
        return StateStatus.NO_FILES_FOUND_FOLDER_DELETED
    if root_locked:
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


def get_text_patterns(text: str, fmt: str) -> tuple[re.Pattern, ...]:
    """Get regex patterns from comma-separated text."""
    split = set(text.split(","))
    return tuple(re.compile(fmt.format(re.escape(t)), re.IGNORECASE) for t in split)
