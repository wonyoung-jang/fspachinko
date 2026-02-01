"""Utility functions for file-roulette."""

import contextlib
import json
import os
import shutil
from filecmp import cmp
from typing import Any

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


def are_paths_equal(path1: str, path2: str) -> bool:
    """Compare two paths for equality, accounting for case sensitivity."""
    if cmp(path1, path2, shallow=True):
        return True
    return cmp(path1, path2, shallow=False)


def load_json(path: str) -> dict[str, Any]:
    """Load JSON data from a file and return as a dictionary."""
    if not (os.path.exists(path) and os.path.isfile(path)):
        return {}

    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict[str, Any]) -> None:
    """Save a dictionary as JSON data to a file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        data = dict(sorted(data.items(), key=lambda item: item[0]))
        json.dump(data, f, indent=4)
