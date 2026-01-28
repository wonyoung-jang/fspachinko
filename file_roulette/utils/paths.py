"""General paths class and utilities."""

import os
from dataclasses import dataclass
from typing import ClassVar

import file_roulette


@dataclass(slots=True)
class Paths:
    """Dataclass for general directories used in File Roulette."""

    pkg: ClassVar[str] = os.path.dirname(file_roulette.__file__ if file_roulette.__file__ else "")
    proj: ClassVar[str] = os.path.dirname(pkg)
    icons: ClassVar[str] = os.path.join(proj, "icons")
    configs: ClassVar[str] = os.path.join(proj, "file_roulette_configs")
    profiles: ClassVar[str] = os.path.join(proj, "file_roulette_profiles")

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
