"""Utility functions for mandala."""

import contextlib
import os
import shutil

from .constants import FALSE_STRS, TRUE_STRS, BytesIn, ByteUnit


class SafeDict(dict):
    """A helper class for string formatting.

    If a key is missing, it returns the key wrapped in braces
    instead of raising a KeyError.
    """

    def __missing__(self, key: str) -> str:
        """Return the key wrapped in braces if missing."""
        return "{" + key + "}"


def calc_unique_path_name(dest: str, stem_or_name: str, ext: str = "") -> str:
    """Calculate a unique path name in the destination."""
    target = os.path.join(dest, f"{stem_or_name}{ext}")

    x = 2
    while os.path.exists(target):
        target = os.path.join(dest, f"{stem_or_name} ({x}){ext}")
        x += 1

    return target


def strtobool(*, val: str | int | bool) -> bool:
    """Convert a string representation of truth to true (1) or false (0).

    Replaces distutils.util.strtobool function (deprecated in Python 3.10).

    True values are: y, yes, t, true, on, 1
    False values are: n, no, f, false, off, 0

    Raises ValueError if val is anything else.
    """
    if isinstance(val, bool):
        return val

    val_str = str(val).casefold()

    if val_str in TRUE_STRS:
        return True

    if val_str in FALSE_STRS:
        return False

    msg = f"Invalid truth value {val!r}"
    raise ValueError(msg)


def convert_string_to_list(string: str, sep: str = ",") -> tuple[str, ...]:
    """Convert a comma-separated string to a list."""
    if not string:
        return ()

    li = tuple(s.strip() for s in string.split(sep))
    if len(li) == 1 and li[0] == "":
        return ()
    return li


def convert_byte_to_size(nbytes: int) -> str:
    """Convert bytes to human readable string."""
    if nbytes < BytesIn.KILOBYTE:
        return f"{nbytes} {ByteUnit.BYTES}"

    if nbytes < BytesIn.MEGABYTE:
        return f"{round(nbytes / BytesIn.KILOBYTE, 2)} {ByteUnit.KILOBYTES}"

    if nbytes < BytesIn.GIGABYTE:
        return f"{round(nbytes / BytesIn.MEGABYTE, 2)} {ByteUnit.MEGABYTES}"

    return f"{round(nbytes / BytesIn.GIGABYTE, 2)} {ByteUnit.GIGABYTES}"


def remove_directory(path: str) -> None:
    """Remove a directory and its contents."""
    with contextlib.suppress(OSError):
        shutil.rmtree(path)
