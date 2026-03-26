"""Filesystem port adapter."""

import logging
import shutil
from dataclasses import dataclass
from filecmp import cmp
from os import mkdir, scandir
from os.path import dirname, exists, join
from typing import TYPE_CHECKING

from fspachinko.constants import DefaultPath

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class DataPaths:
    """Dataclass for general directories used."""

    data: str = join(dirname(DefaultPath.APP), DefaultPath.DATA_DIR)
    icons: str = join(data, DefaultPath.ICON_DIR)
    configs: str = join(data, DefaultPath.CONFIG_DIR)
    profiles: str = join(data, DefaultPath.GUI_PROFILE_DIR)
    logs: str = join(data, DefaultPath.LOG_DIR)

    def __post_init__(self) -> None:
        """Ensure that all paths are absolute."""
        for path in (self.data, self.icons, self.configs, self.profiles, self.logs):
            if not exists(path):
                mkdir(path)

    def get_icon(self, path: str) -> str:
        """Get the full path to an icon."""
        return join(self.icons, path)

    def get_config(self, path: str) -> str:
        """Get the full path to a config file."""
        return join(self.configs, path)

    def get_profile(self, path: str) -> str:
        """Get the full path to a profile file."""
        return join(self.profiles, path)

    def get_log(self, path: str) -> str:
        """Get the full path to a log file."""
        return join(self.logs, path)


_datapaths = DataPaths()
get_icon_path = _datapaths.get_icon
get_config_path = _datapaths.get_config
get_profile_path = _datapaths.get_profile
get_log_path = _datapaths.get_log


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
