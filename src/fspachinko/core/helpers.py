"""Utility functions."""

import logging
import shutil
import subprocess
from dataclasses import dataclass
from filecmp import cmp
from os import mkdir
from os.path import dirname, exists, join

import fspachinko

from .constants import DURATION_CMD, BytesIn, ByteUnit, DefaultPath

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DataPaths:
    """Dataclass for general directories used."""

    pkg: str = dirname(fspachinko.__file__)
    data: str = join(pkg, DefaultPath.DATA_DIR)
    icons: str = join(data, DefaultPath.ICON_DIR)
    configs: str = join(data, DefaultPath.CONFIG_DIR)
    profiles: str = join(data, DefaultPath.GUI_PROFILE_DIR)
    logs: str = join(data, DefaultPath.LOG_DIR)

    def __post_init__(self) -> None:
        """Ensure necessary directories exist."""
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


def calc_unique_path_name_joined(name: str) -> str:
    """Calculate a unique path name in the destination."""
    target = name
    x = 2
    while exists(target):
        target = f"{name} ({x})"
        x += 1
    return target


def remove_directory(path: str) -> None:
    """Remove a directory and its contents."""
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        logger.exception("Directory not found for removal: %s", path)
    except OSError:
        logger.exception("Error occurred while removing directory: %s", path)


def are_files_equal(src: str, dest: str) -> bool:
    """Check if two files are the same by comparing their contents."""
    if cmp(src, dest, shallow=True):
        return cmp(src, dest, shallow=False)
    return False


def get_new_fpath(dest: str, stem: str, ext: str) -> str:
    """Get a new file path, ensuring it doesn't already exist."""
    target = join(dest, f"{stem}{ext}")
    x = 2
    while exists(target):
        target = join(dest, f"{stem} ({x}){ext}")
        x += 1
    return target


def get_duration(path: str) -> float:
    """Get the duration of a media file."""
    try:
        completed_proc = subprocess.run(
            [*DURATION_CMD, path],
            timeout=5,
            check=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
        )
        try:
            return float(completed_proc.stdout.strip())
        except ValueError:
            logger.exception("ffprobe output could not be parsed as float: %s", completed_proc)
            return 0.0
    except subprocess.CalledProcessError:
        logger.exception("ffprobe failed")
        return 0.0
    except subprocess.TimeoutExpired:
        logger.exception("ffprobe timed out for file: %s", path)
        return 0.0


def convert_byte_to_human_readable_size(nbytes: int) -> str:
    """Convert bytes to human readable string."""
    conversion: dict[BytesIn, str] = {
        BytesIn.KILOBYTE: f"{nbytes / BytesIn.BYTE:.2f} {ByteUnit.BYTES}",
        BytesIn.MEGABYTE: f"{nbytes / BytesIn.KILOBYTE:.2f} {ByteUnit.KILOBYTES}",
        BytesIn.GIGABYTE: f"{nbytes / BytesIn.MEGABYTE:.2f} {ByteUnit.MEGABYTES}",
    }
    for threshold, r_str in conversion.items():
        if nbytes < threshold:
            return r_str
    return f"{nbytes / BytesIn.GIGABYTE:.2f} {ByteUnit.GIGABYTES}"
