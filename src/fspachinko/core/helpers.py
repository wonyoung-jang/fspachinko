"""Utility functions."""

import contextlib
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


def convert_string_to_list(string: str, sep: str = ",") -> tuple[str, ...]:
    """Convert a comma-separated string to a list."""
    if not string:
        return ()
    li = tuple(s.strip() for s in string.split(sep))
    if len(li) == 1 and li[0] == "":
        return ()
    return li


def convert_byte_to_human_readable_size(nbytes: int) -> str:
    """Convert bytes to human readable string."""
    if nbytes < BytesIn.KILOBYTE:
        result = f"{nbytes / BytesIn.BYTE:.2f} {ByteUnit.BYTES}"
    elif nbytes < BytesIn.MEGABYTE:
        result = f"{nbytes / BytesIn.KILOBYTE:.2f} {ByteUnit.KILOBYTES}"
    elif nbytes < BytesIn.GIGABYTE:
        result = f"{nbytes / BytesIn.MEGABYTE:.2f} {ByteUnit.MEGABYTES}"
    else:
        result = f"{nbytes / BytesIn.GIGABYTE:.2f} {ByteUnit.GIGABYTES}"
    return result


def remove_directory(path: str) -> None:
    """Remove a directory and its contents."""
    with contextlib.suppress(OSError):
        shutil.rmtree(path)


def are_paths_equal(path1: str, path2: str) -> bool:
    """Compare two paths for equality, accounting for case sensitivity."""
    return cmp(path1, path2, shallow=True) and cmp(path1, path2, shallow=False)


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
    except subprocess.CalledProcessError as e:
        completed_proc = e.output
        code = e.returncode
        logger.exception("ffprobe failed with code %d: %s", code, completed_proc.decode(errors="ignore"))
        return 0.0
    except subprocess.TimeoutExpired:
        logger.exception("ffprobe timed out for file: %s", path)
        return 0.0
