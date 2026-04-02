"""Data paths for the application."""

from enum import StrEnum
from functools import cache
from os import mkdir
from os.path import dirname, exists, join

from fspachinko.constants import DefaultPath


class DataPath(StrEnum):
    """Enum for data paths."""

    DATA = join(dirname(DefaultPath.APP), DefaultPath.DATA_DIR)
    ICONS = join(DATA, DefaultPath.ICON_DIR)
    CONFIGS = join(DATA, DefaultPath.CONFIG_DIR)
    LOGS = join(DATA, DefaultPath.LOG_DIR)


for path in (DataPath.DATA, DataPath.ICONS, DataPath.CONFIGS, DataPath.LOGS):
    if not exists(path):
        mkdir(path)


@cache
def get_icon_path(path: str, icons_dir: str = DataPath.ICONS) -> str:
    """Get the full path to an icon."""
    return join(icons_dir, path)


@cache
def get_config_path(path: str, configs_dir: str = DataPath.CONFIGS) -> str:
    """Get the full path to a config file."""
    return join(configs_dir, path)


@cache
def get_log_path(path: str, logs_dir: str = DataPath.LOGS) -> str:
    """Get the full path to a log file."""
    return join(logs_dir, path)
