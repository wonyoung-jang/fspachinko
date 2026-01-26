"""General paths class and utilities."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import mandala


@dataclass(slots=True)
class Paths:
    """Dataclass for general directories used in Mandala."""

    pkg: ClassVar[Path] = Path(mandala.__file__ if mandala.__file__ else "").parent
    proj: ClassVar[Path] = pkg.parent
    icons: ClassVar[Path] = proj / "icons"
    configs: ClassVar[Path] = proj / "mandala_configs"
    profiles: ClassVar[Path] = proj / "mandala_profiles"

    @classmethod
    def icon(cls, path: str) -> Path:
        """Get the full path to an icon."""
        return cls.icons / path

    @classmethod
    def config(cls, path: str) -> Path:
        """Get the full path to a config file."""
        return cls.configs / path
