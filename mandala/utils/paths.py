"""General paths class and utilities."""

import os
from dataclasses import dataclass
from typing import ClassVar

import mandala


@dataclass(slots=True)
class Paths:
    """Dataclass for general directories used in Mandala."""

    pkg: ClassVar[str] = os.path.dirname(mandala.__file__ if mandala.__file__ else "")
    proj: ClassVar[str] = os.path.dirname(pkg)
    icons: ClassVar[str] = os.path.join(proj, "icons")
    configs: ClassVar[str] = os.path.join(proj, "mandala_configs")
    profiles: ClassVar[str] = os.path.join(proj, "mandala_profiles")

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
