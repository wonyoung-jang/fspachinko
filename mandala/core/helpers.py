"""Core helpers for Mandala."""

from __future__ import annotations

from contextlib import suppress
from filecmp import cmp
from typing import TYPE_CHECKING

from send2trash import send2trash

if TYPE_CHECKING:
    from pathlib import Path

    from ..config.schemas import FilenameModel, FolderModel


def trash_path(path: Path, *, condition: bool) -> None:
    """Trash a path if the condition is met."""
    if condition:
        with suppress(Exception):
            send2trash(path)


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
    is_index = model.is_index
    is_rename = model.is_rename
    name = chosen.name
    if is_index:
        name = f"{index + 1}_{stem}{ext}"
    elif is_rename:
        name = f"{model.rename_to}_{index + 1}{ext}"

    target = dest / name
    target_stem = target.stem
    if target.exists():
        if target.stat().st_size == chosen.stat().st_size:
            if cmp(chosen, target) and not (is_rename or is_index):
                return None
        else:
            return _calc_unique_path_name(dest, target_stem, ext)
    else:
        return target

    return None


def get_status_header(*, success: bool, stopped: bool, none_found: bool, timeout: bool, all_searched: bool) -> str:
    """Generate a status header based on the processing outcome."""
    prefix = "FINISHED (Unknown reason)"
    if success:
        prefix = "SUCCESS"
    elif stopped:
        prefix = "STOPPED"
    elif none_found:
        prefix = "NO FILES FOUND"
        if timeout:
            prefix += "| Reason - timed out"
        elif all_searched:
            prefix += "| Reason - all files searched"
        prefix += " | folder deleted"
    elif all_searched:
        prefix = "ALL FILES SEARCHED"
    elif timeout:
        prefix = "TIMED OUT"
    return prefix


def get_multiplier(unit: str, mapping: dict[str, int]) -> int:
    """Get the multiplier for a given unit from the provided map."""
    return mapping.get(unit, 1)
