"""Filesystem port adapter."""

import logging
import shutil
from dataclasses import dataclass
from filecmp import cmp
from io import UnsupportedOperation
from os import link, makedirs, mkdir, symlink, unlink
from os.path import basename, dirname, exists, join, split
from shutil import copy, copy2, move
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

import fspachinko
from fspachinko.constants import INVALID_FILENAME_CHARS, DefaultPath, FileError, FilenameTemplateMapKey, TransferMode

if TYPE_CHECKING:
    from collections.abc import Callable

    from fspachinko.domain.model import FSEntry


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class DataPaths:
    """Dataclass for general directories used."""

    data: str = join(dirname(fspachinko.__file__), DefaultPath.DATA_DIR)
    icons: str = join(data, DefaultPath.ICON_DIR)
    configs: str = join(data, DefaultPath.CONFIG_DIR)
    profiles: str = join(data, DefaultPath.GUI_PROFILE_DIR)
    logs: str = join(data, DefaultPath.LOG_DIR)

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


def ensure_datapaths(dp: DataPaths) -> None:
    """Ensure necessary directories exist."""
    for path in (dp.data, dp.icons, dp.configs, dp.profiles, dp.logs):
        if not exists(path):
            mkdir(path)


_datapaths = DataPaths()
ensure_datapaths(_datapaths)
get_icon_path = _datapaths.get_icon
get_config_path = _datapaths.get_config
get_profile_path = _datapaths.get_profile
get_log_path = _datapaths.get_log


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


def get_available_transfer_modes() -> dict[TransferMode, Callable]:
    """Return the set of available transfer modes based on the current environment."""
    available = AVAILABLE_TRANSFER_FNS

    def _verify_link_fn(link_func: Callable[[str, str], None], transfer_mode: TransferMode) -> None:
        """Test link creation."""
        try:
            with TemporaryDirectory() as tmpdir:
                test_src = join(tmpdir, "test_src")
                test_link = join(tmpdir, "test_link")
                open(test_src, "w").close()
                link_func(test_src, test_link)
                unlink(test_link)
                unlink(test_src)
        except OSError, UnsupportedOperation, NotImplementedError:
            available.pop(transfer_mode)

    _verify_link_fn(symlink, TransferMode.SYMLINK)
    _verify_link_fn(link, TransferMode.HARDLINK)
    return available


def hardlink(src: str, dst: str) -> None:
    """Create a hardlink from source to destination."""
    try:
        link(src, dst)
    except OSError as e:
        is_win_x_error = e.winerror == FileError.WINDOWS_CROSS_DRIVE_ERROR
        is_unix_x_error = e.errno == FileError.UNIX_CROSS_FILESYSTEM_ERROR
        if is_win_x_error or is_unix_x_error:
            symlink(src, dst)
        else:
            raise


AVAILABLE_TRANSFER_FNS = {
    TransferMode.DRY_RUN: lambda _, __: None,
    TransferMode.COPY: copy,
    TransferMode.COPY_PRESERVE: copy2,
    TransferMode.MOVE: move,
    TransferMode.SYMLINK: symlink,
    TransferMode.HARDLINK: hardlink,
}


def get_name_from_template(entry: FSEntry, count: int, template: str) -> str:
    """Calculate the destination file stem based on template configuration."""
    mapping = SafeDict(
        {
            FilenameTemplateMapKey.INDEX: count + 1,
            FilenameTemplateMapKey.ORIGINAL: entry.stem,
            FilenameTemplateMapKey.PARENT: basename(entry.parent),
            FilenameTemplateMapKey.PARENTS_TO_ROOT: split(entry.path)[0],
        }
    )
    try:
        formatted_stem = template.format_map(mapping)
        return "".join(c for c in formatted_stem if c not in INVALID_FILENAME_CHARS)
    except KeyError, ValueError, IndexError:
        return entry.stem


class SafeDict(dict):
    """A helper class for string formatting.

    If a key is missing, it returns the key wrapped in braces
    instead of raising a KeyError.
    """

    def __missing__(self, key: str) -> str:
        """Return the key wrapped in braces if missing."""
        return "{" + key + "}"
