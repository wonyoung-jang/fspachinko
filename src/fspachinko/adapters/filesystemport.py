"""Filesystem port adapter."""

import logging
import shutil
from filecmp import cmp
from os import makedirs, mkdir
from os.path import exists, join, split
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .datapaths import DataPaths

logger = logging.getLogger(__name__)


def ensure_datapaths(dp: DataPaths) -> None:
    """Ensure necessary directories exist."""
    for path in (dp.data, dp.icons, dp.configs, dp.profiles, dp.logs):
        if not exists(path):
            mkdir(path)


def get_unique_path(dest: str, stem: str, ext: str = "") -> str:
    """Get a new path, ensuring it doesn't already exist."""
    target = join(dest, f"{stem}{ext}")
    x = 2
    while exists(target):
        target = join(dest, f"{stem} ({x}){ext}")
        x += 1
    return target


def are_files_equal(src: str, dest: str) -> bool:
    """Check if two files are the same by comparing their contents."""
    if not exists(dest):
        return False
    if cmp(src, dest, shallow=True):
        return cmp(src, dest, shallow=False)
    return False


def get_dest_dir_path(dest: str) -> str:
    """Get the destination directory path."""
    new_dest = get_unique_path(*split(dest))
    makedirs(new_dest, exist_ok=True)
    return new_dest


def remove_directory(path: str) -> None:
    """Remove a directory and its contents, with error handling."""
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        logger.exception("Directory not found for removal: %s", path)
    except OSError:
        logger.exception("Error occurred while removing directory: %s", path)
