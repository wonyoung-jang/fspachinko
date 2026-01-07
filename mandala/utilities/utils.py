"""Utility functions for mandala."""

from __future__ import annotations

from ..config.constants import BYTE_TO_GIGABYTE, BYTE_TO_MEGABYTE, BYTES_IN_GIGABYTE


def strtobool(val: str) -> bool:
    """Convert a string representation of truth to true (1) or false (0).

    Replaces distutils.util.strtobool function (deprecated in Python 3.10).

    True values are: y, yes, t, true, on, 1
    False values are: n, no, f, false, off, 0

    Raises ValueError if val is anything else.
    """
    val_lower = str(val).lower()

    if val_lower in ("y", "yes", "t", "true", "on", "1"):
        return True

    if val_lower in ("n", "no", "f", "false", "off", "0"):
        return False

    msg = f"invalid truth value {val!r}"
    raise ValueError(msg)


def convert_byte_to_size(bytes_in_curr_dir: int) -> str:
    """Convert bytes to MB or GB string."""
    if bytes_in_curr_dir < BYTES_IN_GIGABYTE - 1:
        return f"{round(bytes_in_curr_dir * BYTE_TO_MEGABYTE, 2)} MB"
    return f"{round(bytes_in_curr_dir * BYTE_TO_GIGABYTE, 2)} GB"


def convert_string_to_list(string: str, sep: str = " ") -> list[str]:
    """Convert a space-separated string to a list."""
    li = string.split(sep)
    if len(li) == 1 and li[0] == "":
        return []
    return li
