"""Data paths for the application."""

from functools import cache
from os import mkdir
from os.path import dirname, exists, join

from fspachinko.fp import Fp


@cache
def data_path() -> str:
    """Get the full path to a data file."""
    return join(dirname(Fp.Paths.APP), Fp.Paths.DATA_DIR)


@cache
def icons_path() -> str:
    """Get the full path to the icons directory."""
    return join(data_path(), Fp.Paths.ICON_DIR)


@cache
def configs_path() -> str:
    """Get the full path to the configs directory."""
    return join(data_path(), Fp.Paths.CONFIG_DIR)


@cache
def logs_path() -> str:
    """Get the full path to the logs directory."""
    return join(data_path(), Fp.Paths.LOG_DIR)


def ensure_data_paths() -> None:
    """Ensure that all necessary data paths exist."""
    for path in (data_path(), icons_path(), configs_path(), logs_path()):
        if not exists(path):
            mkdir(path)


@cache
def get_icon_path(path: str) -> str:
    """Get the full path to an icon."""
    return join(icons_path(), path)


@cache
def get_config_path(path: str) -> str:
    """Get the full path to a config file."""
    return join(configs_path(), path)


@cache
def get_log_path(path: str) -> str:
    """Get the full path to a log file."""
    return join(logs_path(), path)
