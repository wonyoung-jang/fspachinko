"""Utility functions for mandala."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from filecmp import cmp
from typing import TYPE_CHECKING, ClassVar, Self

if TYPE_CHECKING:
    from pathlib import Path

    from ..config.schemas import FilenameModel, FolderModel


class SafeDict(dict):
    """A helper class for string formatting.

    If a key is missing, it returns the key wrapped in braces
    instead of raising a KeyError.
    """

    def __missing__(self, key: str) -> str:
        """Return the key wrapped in braces if missing."""
        return "{" + key + "}"


@dataclass(slots=True)
class DateTimeSingleton:
    """Singleton for current date and time."""

    now: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    instance: ClassVar[DateTimeSingleton]

    def __new__(cls) -> Self:
        """Ensure only one instance exists."""
        if not hasattr(cls, "instance"):
            cls.instance = super(DateTimeSingleton, cls).__new__(cls)
        return cls.instance


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


def calc_dest_file_path(model: FilenameModel, chosen: Path, dest: Path, index: int) -> Path | None:
    """Calculate the destination file path based on naming conventions."""
    ext = chosen.suffix
    stem = chosen.stem

    mapping = {
        "original": stem,
        "index": index + 1,
        "date": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        "time": datetime.now(tz=UTC).strftime("%H-%M-%S"),
        "datetime": datetime.now(tz=UTC).strftime("%Y-%m-%d_%H-%M-%S"),
        "parent": chosen.parent.name,
        "parentstoroot": "_".join(chosen.parts[:-1]),
    }
    safe_map = SafeDict(mapping)

    try:
        new_stem = model.template.format_map(safe_map)
    except (KeyError, ValueError):
        new_stem = stem

    invalid_chars = r'\/:*?"<>|'
    new_stem = "".join(c for c in new_stem if c not in invalid_chars)
    name = f"{new_stem}{ext}"

    target = dest / name

    if target.exists():
        if target.stat().st_size == chosen.stat().st_size:
            if cmp(chosen, target, shallow=False):
                return None
        else:
            return _calc_unique_path_name(dest, target.stem, ext)
    else:
        return target

    return None


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
