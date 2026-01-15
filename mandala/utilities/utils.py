"""Utility functions for mandala."""

from __future__ import annotations


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


def convert_string_to_list(string: str, sep: str = " ") -> list[str]:
    """Convert a space-separated string to a list."""
    li = string.split(sep)
    if len(li) == 1 and li[0] == "":
        return []
    return li
