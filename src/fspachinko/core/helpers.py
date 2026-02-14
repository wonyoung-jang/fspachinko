"""Utility functions."""

import contextlib
import logging
import shutil
from dataclasses import dataclass
from filecmp import cmp
from os import mkdir
from os.path import basename, dirname, exists, join, splitext
from subprocess import DEVNULL, CalledProcessError, check_output

import fspachinko

from .constants import DURATION_CMD, BytesIn, ByteUnit

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DataPaths:
    """Dataclass for general directories used."""

    pkg: str = dirname(fspachinko.__file__)
    data: str = join(pkg, "_data")
    icons: str = join(data, "icons")
    configs: str = join(data, "configs")
    profiles: str = join(data, "gui_profiles")

    def __post_init__(self) -> None:
        """Ensure necessary directories exist."""
        if not exists(self.profiles):
            mkdir(self.profiles)

    def get_icon(self, path: str) -> str:
        """Get the full path to an icon."""
        return join(self.icons, path)

    def get_config(self, path: str) -> str:
        """Get the full path to a config file."""
        return join(self.configs, path)

    def get_profile(self, path: str) -> str:
        """Get the full path to a profile file."""
        return join(self.profiles, path)


_datapaths = DataPaths()
get_icon_path = _datapaths.get_icon
get_config_path = _datapaths.get_config
get_profile_path = _datapaths.get_profile


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
        return f"{nbytes} {ByteUnit.BYTES}"

    if nbytes < BytesIn.MEGABYTE:
        return f"{round(nbytes / BytesIn.KILOBYTE, 2)} {ByteUnit.KILOBYTES}"

    if nbytes < BytesIn.GIGABYTE:
        return f"{round(nbytes / BytesIn.MEGABYTE, 2)} {ByteUnit.MEGABYTES}"

    return f"{round(nbytes / BytesIn.GIGABYTE, 2)} {ByteUnit.GIGABYTES}"


def remove_directory(path: str) -> None:
    """Remove a directory and its contents."""
    with contextlib.suppress(OSError):
        shutil.rmtree(path)


def are_paths_equal(path1: str, path2: str) -> bool:
    """Compare two paths for equality, accounting for case sensitivity."""
    if cmp(path1, path2, shallow=True):
        return True
    return cmp(path1, path2, shallow=False)


def get_stem_and_ext(path: str) -> tuple[str, str]:
    """Get the stem and extension of a file path."""
    return splitext(basename(path))


def get_duration(path: str) -> float:
    """Get the duration of a media file."""
    try:
        out_bytes = check_output(
            [*DURATION_CMD, path],
            stderr=DEVNULL,
            timeout=10,
        )
        try:
            return float(out_bytes.decode().strip())
        except ValueError:
            logger.debug("ffprobe output could not be parsed as float: %s", out_bytes.decode(errors="ignore"))
            return 0.0
    except CalledProcessError as e:
        out_bytes = e.output
        code = e.returncode
        logger.debug("ffprobe failed with code %d: %s", code, out_bytes.decode(errors="ignore"))
        return 0.0
