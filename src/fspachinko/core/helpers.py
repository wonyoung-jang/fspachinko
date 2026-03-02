"""Utility functions."""

import logging
from dataclasses import dataclass
from os.path import dirname, join

import fspachinko

from ..adapters.filesystemport import ensure_datapaths
from .constants import BytesIn, ByteUnit, DefaultPath, StateStatus

logger = logging.getLogger(__name__)


@dataclass(slots=True)
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


_datapaths = DataPaths()
ensure_datapaths(_datapaths)
get_icon_path = _datapaths.get_icon
get_config_path = _datapaths.get_config
get_profile_path = _datapaths.get_profile
get_log_path = _datapaths.get_log


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


def get_status(
    *, is_success: bool, is_none_found: bool, is_stop_requested: bool, is_create_dir: bool, is_root_locked: bool
) -> str | StateStatus:
    """Get the state and message for reporting."""
    if is_success:
        return StateStatus.SUCCESS
    if is_stop_requested:
        return StateStatus.USER_STOPPED
    if is_none_found and is_create_dir and is_root_locked:
        return StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED
    if is_none_found and is_create_dir:
        return StateStatus.NO_FILES_FOUND_FOLDER_DELETED
    if is_root_locked:
        return StateStatus.ALL_FILES_SEARCHED
    return StateStatus.UNDEFINED


def get_report(path: str, size_str: str, runtime_str: str, count: int, target_qty: int) -> str:
    """Generate a summary report string."""
    return (
        "------------------------------------------------------------------------\n"
        f"{count}/{target_qty} files transferred\n"
        "------------------------------------------------------------------------\n"
        f"Destination:  {path}\n"
        f"Size:         {size_str}\n"
        f"Runtime:      {runtime_str}\n"
        "========================================================================\n"
    )
