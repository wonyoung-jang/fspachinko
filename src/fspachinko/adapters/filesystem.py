"""Filesystem port adapter."""

import json
import logging
import shutil
from abc import ABC, abstractmethod
from filecmp import cmp
from os import mkdir, scandir
from os.path import exists, isfile, join
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)


class AbstractFilesystem(ABC):
    """Abstract interface for filesystem operations."""

    @abstractmethod
    def get_unique_path(self, path: str, paths: Iterable[str]) -> str:
        """Get a new path, ensuring it doesn't already exist."""

    @abstractmethod
    def are_files_identical(self, f1: str, f2: str) -> bool:
        """Check if two files are identical by comparing their contents."""

    @abstractmethod
    def get_existing_subdirs(self, path: str) -> set[str]:
        """Get a set of existing directory paths within the specified path."""

    @abstractmethod
    def join_path(self, *parts: str) -> str:
        """Join path parts into a single path."""

    @abstractmethod
    def json_to_dict(self, path: str) -> dict:
        """Load JSON data from a file."""

    @abstractmethod
    def save_json(self, path: str, data: dict) -> None:
        """Save JSON data to a file."""

    @abstractmethod
    def make_directory(self, path: str) -> None:
        """Create a directory at the specified path."""

    @abstractmethod
    def remove_directory(self, path: str) -> None:
        """Remove a directory and its contents, with error handling."""


class Filesystem(AbstractFilesystem):
    """Concrete implementation of AbstractFilesystem using the local filesystem."""

    def get_unique_path(self, path: str, paths: Iterable[str]) -> str:
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

    def are_files_identical(self, f1: str, f2: str) -> bool:
        """Check if two files are identical by comparing their contents."""
        if cmp(f1, f2, shallow=True):
            return cmp(f1, f2, shallow=False)
        return False

    def get_existing_subdirs(self, path: str) -> set[str]:
        """Get a set of existing directory paths within the specified path."""
        return {e.path for e in scandir(path) if e.is_dir()}

    def join_path(self, *parts: str) -> str:
        """Join path parts into a single path."""
        return join(*parts)

    def json_to_dict(self, path: str) -> dict:
        """Load JSON data from a file."""
        if exists(path) and isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_json(self, path: str, data: dict) -> None:
        """Save JSON data to a file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def remove_directory(self, path: str) -> None:
        """Remove a directory and its contents, with error handling."""
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            logger.exception("Directory not found for removal: %s", path)
        except OSError:
            logger.exception("Error occurred while removing directory: %s", path)

    def make_directory(self, path: str) -> None:
        """Create a directory at the specified path."""
        mkdir(path)
