"""Utility functions."""

import re

from .constants import SIZE_MAP, StateStatus


def convert_byte_to_human_readable_size(nbytes: int) -> str:
    """Convert bytes to human readable string."""
    for unit, threshold in SIZE_MAP.items():
        if nbytes < threshold * 1024:
            result = f"{nbytes / threshold:.2f} {unit}"
            break
    return result


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


def get_text_patterns(text: str, fmt: str) -> tuple[re.Pattern, ...]:
    """Get regex patterns from comma-separated text."""

    def compile_re(t: str) -> re.Pattern:
        return re.compile(fmt.format(re.escape(t)), re.IGNORECASE)

    split = set(text.split(","))
    return tuple(compile_re(t) for t in split)
