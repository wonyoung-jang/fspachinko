"""Manager class for configuration files."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fspachinko.datapaths import configs_path, get_config_path

if TYPE_CHECKING:
    from fspachinko.adapters.filesystem import AbstractFilesystem


@dataclass(slots=True)
class ConfigManager:
    """Manager for configuration files."""

    fs: AbstractFilesystem
    directory: str = configs_path()
    _current: str = ""

    @property
    def current(self) -> str:
        """Get the current configuration file name."""
        return self._current

    @current.setter
    def current(self, p: str) -> None:
        """Set the current configuration file name."""
        self._current = get_config_path(p)

    def get_configs(self) -> list[str]:
        """Get a list of available configuration files."""
        return self.fs.get_existing_json_files(self.directory)
