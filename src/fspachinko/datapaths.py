"""Data paths for the application."""

from dataclasses import dataclass
from os import mkdir
from os.path import dirname, exists, join

from fspachinko.constants import DefaultPath

_DATA: str = join(dirname(DefaultPath.APP), DefaultPath.DATA_DIR)


@dataclass(slots=True, frozen=True)
class DataPaths:
    """Dataclass for general directories used."""

    icons: str = join(_DATA, DefaultPath.ICON_DIR)
    configs: str = join(_DATA, DefaultPath.CONFIG_DIR)
    logs: str = join(_DATA, DefaultPath.LOG_DIR)

    def __post_init__(self) -> None:
        """Ensure that all paths are absolute."""
        for path in (_DATA, self.icons, self.configs, self.logs):
            if not exists(path):
                mkdir(path)

    def icon(self, path: str) -> str:
        """Get the full path to an icon."""
        return join(self.icons, path)

    def config(self, path: str) -> str:
        """Get the full path to a config file."""
        return join(self.configs, path)

    def log(self, path: str) -> str:
        """Get the full path to a log file."""
        return join(self.logs, path)


DATA_PATHS = DataPaths()
get_icon_path = DATA_PATHS.icon
get_config_path = DATA_PATHS.config
get_log_path = DATA_PATHS.log
