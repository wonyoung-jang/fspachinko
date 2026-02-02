"""General paths class and utilities."""

import os
from dataclasses import dataclass
from typing import ClassVar

import galton


@dataclass(slots=True)
class Paths:
    """Dataclass for general directories used."""

    pkg: ClassVar[str] = os.path.dirname(galton.__file__)
    data: ClassVar[str] = os.path.join(pkg, "_data")
    icons: ClassVar[str] = os.path.join(data, "icons")
    configs: ClassVar[str] = os.path.join(data, "configs")
    profiles: ClassVar[str] = os.path.join(data, "gui_profiles")

    @classmethod
    def icon(cls, path: str) -> str:
        """Get the full path to an icon."""
        return os.path.join(cls.icons, path)

    @classmethod
    def config(cls, path: str) -> str:
        """Get the full path to a config file."""
        return os.path.join(cls.configs, path)

    @classmethod
    def profile(cls, path: str) -> str:
        """Get the full path to a profile file."""
        return os.path.join(cls.profiles, path)
