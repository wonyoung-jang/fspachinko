"""Data paths for the application."""

from functools import cache
from os import mkdir
from os.path import dirname, exists, join

from fspachinko.fp import Fp


@cache
def _data_path() -> str:
    """Get the full path to a data file."""
    return join(dirname(Fp.Path.APP), Fp.Path.DATA_DIR)


@cache
def cache_path() -> str:
    """Get the full path to the cache directory."""
    return join(_data_path(), Fp.Path.CACHE_DIR)


@cache
def configs_path() -> str:
    """Get the full path to the configs directory."""
    return join(_data_path(), Fp.Path.CONFIG_DIR)


@cache
def icons_path() -> str:
    """Get the full path to the icons directory."""
    return join(_data_path(), Fp.Path.ICON_DIR)


@cache
def logs_path() -> str:
    """Get the full path to the logs directory."""
    return join(_data_path(), Fp.Path.LOG_DIR)


def ensure_data_paths() -> None:
    """Ensure that all necessary data paths exist."""
    for path in (_data_path(), cache_path(), configs_path(), icons_path(), logs_path()):
        if not exists(path):
            mkdir(path)


@cache
def get_cache_path(path: str = Fp.Path.CACHE) -> str:
    """Get the full path to a cache file."""
    return join(cache_path(), path)


@cache
def get_config_path(path: str) -> str:
    """Get the full path to a config file."""
    return join(configs_path(), path)


@cache
def get_icon_path(path: str) -> str:
    """Get the full path to an icon."""
    return join(icons_path(), path)


@cache
def get_log_path(path: str) -> str:
    """Get the full path to a log file."""
    return join(logs_path(), path)
