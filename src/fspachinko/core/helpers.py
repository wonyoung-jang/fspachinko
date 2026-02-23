"""Utility functions."""

import logging
import shutil
import subprocess
from dataclasses import dataclass
from filecmp import cmp
from os import mkdir
from os.path import basename, dirname, exists, join, splitext

import fspachinko

from .constants import DURATION_CMD, INVALID_FILENAME_CHARS, BytesIn, ByteUnit, DefaultPath

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


class SafeDict(dict):
    """A helper class for string formatting.

    If a key is missing, it returns the key wrapped in braces
    instead of raising a KeyError.
    """

    def __missing__(self, key: str) -> str:
        """Return the key wrapped in braces if missing."""
        return "{" + key + "}"


def calc_unique_path_name(dest: str, stem_or_name: str, ext: str = "") -> str:
    """Calculate a unique path name in the destination."""
    target = join(dest, f"{stem_or_name}{ext}")
    x = 2
    while exists(target):
        target = join(dest, f"{stem_or_name} ({x}){ext}")
        x += 1
    return target


def remove_directory(path: str) -> None:
    """Remove a directory and its contents."""
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        logger.warning("Directory not found for removal: %s", path)
    except OSError:
        logger.exception("Error occurred while removing directory: %s", path)


def get_new_fpath(dest: str, path: str, stem: str, ext: str) -> str | None:
    """Get a new file path, ensuring it doesn't already exist."""
    target = join(dest, f"{stem}{ext}")
    if not exists(target):
        return target
    if cmp(path, target) and cmp(path, target, shallow=False):
        return None
    return calc_unique_path_name(dest, stem, ext)


def convert_string_to_tuple(string: str, sep: str = ",") -> tuple[str, ...]:
    """Convert a comma-separated string to a tuple."""
    if not string:
        return ()
    li = tuple(s.strip() for s in string.split(sep))
    if len(li) == 1 and li[0] == "":
        return ()
    return li


def convert_byte_to_human_readable_size(nbytes: int) -> str:
    """Convert bytes to human readable string."""
    result_map = {
        BytesIn.KILOBYTE: f"{nbytes / BytesIn.BYTE:.2f} {ByteUnit.BYTES}",
        BytesIn.MEGABYTE: f"{nbytes / BytesIn.KILOBYTE:.2f} {ByteUnit.KILOBYTES}",
        BytesIn.GIGABYTE: f"{nbytes / BytesIn.MEGABYTE:.2f} {ByteUnit.MEGABYTES}",
    }
    for size_threshold, result in result_map.items():
        if nbytes < size_threshold:
            return result
    return f"{nbytes / BytesIn.GIGABYTE:.2f} {ByteUnit.GIGABYTES}"


def get_stem_and_ext(path: str) -> tuple[str, str]:
    """Get the stem and extension of a file path."""
    return splitext(basename(path))


def get_valid_filename_from_str(name: str) -> str:
    """Remove invalid characters from a filename."""
    return "".join(c for c in name if c not in INVALID_FILENAME_CHARS)


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
