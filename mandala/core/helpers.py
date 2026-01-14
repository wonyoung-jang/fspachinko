"""Core helpers for Mandala."""

from __future__ import annotations

from contextlib import suppress
from filecmp import cmp
from typing import TYPE_CHECKING

from send2trash import send2trash

if TYPE_CHECKING:
    from pathlib import Path

    from ..config.schemas import FilenameModel


def trash_path(path: Path, *, condition: bool) -> None:
    """Trash a path if the condition is met."""
    if condition:
        with suppress(Exception):
            send2trash(path)


def calc_dest_file_path(cfg: FilenameModel, chosen: Path, dest: Path, index: int) -> Path | None:
    """Calculate the destination file path based on naming conventions."""
    ext = chosen.suffix
    stem = chosen.stem
    is_index = cfg.is_index
    is_rename = cfg.is_rename

    if is_index:
        name = f"{index + 1}_{stem}{ext}"
    elif is_rename:
        name = f"{cfg.rename_to}_{index + 1}{ext}"
    else:
        name = chosen.name

    target = dest / name

    if target.exists() and cmp(chosen, target) and not (is_rename or is_index):
        return None

    x = 2
    base_stem = target.stem
    while target.exists():
        target = dest / f"{base_stem} ({x}){ext}"
        x += 1

    return target
