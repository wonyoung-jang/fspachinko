"""Utility functions for mandala."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class SafeDict(dict):
    """A helper class for string formatting.

    If a key is missing, it returns the key wrapped in braces
    instead of raising a KeyError.
    """

    def __missing__(self, key: str) -> str:
        """Return the key wrapped in braces if missing."""
        return "{" + key + "}"


def calc_unique_path_name(dest: Path, stem_or_name: str, ext: str = "") -> Path:
    """Calculate a unique path name in the destination."""
    target = dest / f"{stem_or_name}{ext}"

    x = 2
    while target.exists():
        target = dest / f"{stem_or_name} ({x}){ext}"
        x += 1

    return target


def get_status_header(*, success: bool, stopped: bool, none_found: bool, all_searched: bool) -> str:
    """Generate a status header based on the processing outcome."""
    if success:
        return "SUCCESS"

    if stopped:
        return "STOPPED"

    if none_found and all_searched:
        return "NO FILES FOUND | ALL FILES SEARCHED | folder deleted"

    if none_found:
        return "NO FILES FOUND | folder deleted"

    if all_searched:
        return "ALL FILES SEARCHED"

    return "FINISHED (Unknown reason)"


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

    if val_str in {"y", "yes", "t", "true", "on", "1"}:
        return True

    if val_str in {"n", "no", "f", "false", "off", "0"}:
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
