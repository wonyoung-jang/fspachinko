"""General paths class and utilities."""

import os
from dataclasses import dataclass

import fspachinko


@dataclass(slots=True)
class DataPaths:
    """Dataclass for general directories used."""

    pkg: str = os.path.dirname(fspachinko.__file__)
    data: str = os.path.join(pkg, "_data")
    icons: str = os.path.join(data, "icons")
    configs: str = os.path.join(data, "configs")
    profiles: str = os.path.join(data, "gui_profiles")

    def __post_init__(self) -> None:
        """Ensure necessary directories exist."""
        os.makedirs(self.profiles, exist_ok=True)

    def get_icon(self, path: str) -> str:
        """Get the full path to an icon."""
        return os.path.join(self.icons, path)

    def get_config(self, path: str) -> str:
        """Get the full path to a config file."""
        return os.path.join(self.configs, path)

    def get_profile(self, path: str) -> str:
        """Get the full path to a profile file."""
        return os.path.join(self.profiles, path)


_datapaths = DataPaths()
get_icon = _datapaths.get_icon
get_config = _datapaths.get_config
get_profile = _datapaths.get_profile
