"""Filesystem port adapter."""

import logging
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from filecmp import cmp
from os import makedirs, mkdir
from os.path import exists, join, split
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.helpers import DataPaths

logger = logging.getLogger(__name__)


def ensure_datapaths(dp: DataPaths) -> None:
    """Ensure necessary directories exist."""
    for path in (dp.data, dp.icons, dp.configs, dp.profiles, dp.logs):
        if not exists(path):
            mkdir(path)


def remove_directory(path: str, *, is_create_dir: bool, is_none_found: bool) -> None:
    """Remove a directory and its contents, with error handling."""
    if not (is_create_dir and is_none_found):
        return

    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        logger.exception("Directory not found for removal: %s", path)
    except OSError:
        logger.exception("Error occurred while removing directory: %s", path)


@dataclass(slots=True)
class AbstractFilesystemPort(ABC):
    """Abstract port for filesystem operations."""

    @abstractmethod
    def get_unique_path(self, dest: str, stem: str, ext: str = "") -> str:
        """Get a new file path, ensuring it doesn't already exist."""

    @abstractmethod
    def are_files_equal(self, src: str, dest: str) -> bool:
        """Check if two files are the same by comparing their contents."""

    @abstractmethod
    def get_dest_dir_path(self, dest: str) -> str:
        """Get the destination directory path."""

    @abstractmethod
    def remove_directory(self, path: str) -> None:
        """Remove a directory and its contents, with error handling."""


@dataclass(slots=True)
class ConcreteFilesystemPort(AbstractFilesystemPort):
    """Adapter for filesystem operations."""

    def get_unique_path(self, dest: str, stem: str, ext: str = "") -> str:
        """Get a new path, ensuring it doesn't already exist."""
        target = join(dest, f"{stem}{ext}")
        x = 2
        while exists(target):
            target = join(dest, f"{stem} ({x}){ext}")
            x += 1
        return target

    def are_files_equal(self, src: str, dest: str) -> bool:
        """Check if two files are the same by comparing their contents."""
        if not exists(dest):
            return False
        if cmp(src, dest, shallow=True):
            return cmp(src, dest, shallow=False)
        return False

    def get_dest_dir_path(self, dest: str) -> str:
        """Get the destination directory path."""
        new_dest = self.get_unique_path(*split(dest))
        makedirs(new_dest, exist_ok=True)
        return new_dest

    def remove_directory(self, path: str) -> None:
        """Remove a directory and its contents, with error handling."""
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            logger.exception("Directory not found for removal: %s", path)
        except OSError:
            logger.exception("Error occurred while removing directory: %s", path)
