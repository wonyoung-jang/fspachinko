"""Filesystem port adapter."""

import logging
import shutil
from filecmp import cmp
from os import scandir
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)


def get_unique_path(path: str, paths: Iterable[str]) -> str:
    """Get a new path, ensuring it doesn't already exist."""
    if path not in paths:
        return path
    stem, _, ext = path.rpartition(".")
    if not stem:
        stem, ext = ext, ""
    else:
        ext = f".{ext}"
    x = 2
    while (candidate := f"{stem} ({x}){ext}") in paths:
        x += 1
    return candidate


def are_files_identical(path1: str, path2: str) -> bool:
    """Check if two files are identical by comparing their contents."""
    if cmp(path1, path2, shallow=True):
        return cmp(path1, path2, shallow=False)
    return False


def remove_directory(path: str) -> None:
    """Remove a directory and its contents, with error handling."""
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        logger.exception("Directory not found for removal: %s", path)
    except OSError:
        logger.exception("Error occurred while removing directory: %s", path)


def get_existing_directories(path: str) -> set[str]:
    """Get a set of existing directory paths within the specified path."""
    return {e.path for e in scandir(path) if e.is_dir()}
