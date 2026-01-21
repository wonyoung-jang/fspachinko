"""Utility functions for mandala."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from ..config.schemas import FolderModel


class SafeDict(dict):
    """A helper class for string formatting.

    If a key is missing, it returns the key wrapped in braces
    instead of raising a KeyError.
    """

    def __missing__(self, key: str) -> str:
        """Return the key wrapped in braces if missing."""
        return "{" + key + "}"


def _calc_unique_path_name(dest: Path, stem_or_name: str, ext: str = "") -> Path:
    """Calculate a unique path name in the destination."""
    target = dest / f"{stem_or_name}{ext}"

    x = 2
    while target.exists():
        target = dest / f"{stem_or_name} ({x}){ext}"
        x += 1

    return target


def create_dest_folder(model: FolderModel, dest: Path) -> Path:
    """Create the destination folder based on configuration."""
    if not model.create:
        return dest

    name = model.name
    target = _calc_unique_path_name(dest, name)
    target.mkdir(parents=False)
    return target


def get_status_header(*, success: bool, stopped: bool, none_found: bool, all_searched: bool) -> str:
    """Generate a status header based on the processing outcome."""
    prefix = "FINISHED (Unknown reason)"
    if success:
        prefix = "SUCCESS"
    elif stopped:
        prefix = "STOPPED"
    elif none_found:
        prefix = "NO FILES FOUND"
        if all_searched:
            prefix += "| Reason - all files searched"
        prefix += " | folder deleted"
    elif all_searched:
        prefix = "ALL FILES SEARCHED"
    return prefix


def get_multiplier(unit: str, mapping: dict[str, int]) -> int:
    """Get the multiplier for a given unit from the provided map."""
    return mapping.get(unit, 1)


def strtobool(val: str) -> bool:
    """Convert a string representation of truth to true (1) or false (0).

    Replaces distutils.util.strtobool function (deprecated in Python 3.10).

    True values are: y, yes, t, true, on, 1
    False values are: n, no, f, false, off, 0

    Raises ValueError if val is anything else.
    """
    clean_val = str(val).casefold()

    if clean_val in ("y", "yes", "t", "true", "on", "1"):
        return True

    if clean_val in ("n", "no", "f", "false", "off", "0"):
        return False

    msg = f"Invalid truth value {val!r}"
    raise ValueError(msg)


def convert_string_to_list(string: str, sep: str = " ") -> tuple[str, ...]:
    """Convert a space-separated string to a list."""
    li = tuple(string.split(sep))
    if len(li) == 1 and li[0] == "":
        return ()
    return li
