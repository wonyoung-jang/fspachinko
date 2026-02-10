"""Utility functions."""

import contextlib
import json
import logging
import os
import shutil
from filecmp import cmp
from os.path import basename, dirname, exists, isfile, join, splitext
from subprocess import DEVNULL, CalledProcessError, check_output
from typing import Any

from .constants import DURATION_CMD, BytesIn, ByteUnit

logger = logging.getLogger(__name__)


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
    target = join(dest, f"{stem_or_name}{ext}")

    x = 2
    while exists(target):
        target = join(dest, f"{stem_or_name} ({x}){ext}")
        x += 1

    return target


def convert_string_to_list(string: str, sep: str = ",") -> tuple[str, ...]:
    """Convert a comma-separated string to a list."""
    if not string:
        return ()

    li = tuple(s.strip() for s in string.split(sep))
    if len(li) == 1 and li[0] == "":
        return ()
    return li


def convert_byte_to_human_readable_size(nbytes: int) -> str:
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
    if not (exists(path) and isfile(path)):
        return {}

    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict[str, Any]) -> None:
    """Save a dictionary as JSON data to a file."""
    os.makedirs(dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        data = dict(sorted(data.items(), key=lambda item: item[0]))
        json.dump(data, f, indent=4)


def get_stem_and_ext(path: str) -> tuple[str, str]:
    """Get the stem and extension of a file path."""
    return splitext(basename(path))


def get_duration(path: str) -> float:
    """Get the duration of a media file."""
    try:
        out_bytes = check_output(
            [*DURATION_CMD, path],
            stderr=DEVNULL,
            timeout=10,
        )
        try:
            return float(out_bytes.decode().strip())
        except ValueError:
            logger.debug("ffprobe output could not be parsed as float: %s", out_bytes.decode(errors="ignore"))
            return 0.0
    except CalledProcessError as e:
        out_bytes = e.output
        code = e.returncode
        logger.debug("ffprobe failed with code %d: %s", code, out_bytes.decode(errors="ignore"))
        return 0.0
