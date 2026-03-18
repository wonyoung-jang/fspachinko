"""Settings handling."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from os.path import exists, isfile


@dataclass(slots=True)
class AbstractConfigRepository(ABC):
    """Abstract class for managing configuration profiles."""

    @abstractmethod
    def set(self, dst: str, data: dict) -> None:
        """Save configuration from a dict to the profile path."""

    @abstractmethod
    def get(self, src: str) -> dict:
        """Load configuration from the profile path and return as a dict."""


class JSONConfigRepository(AbstractConfigRepository):
    """Class for managing configuration profiles."""

    def set(self, dst: str, data: dict) -> None:
        """Save JSON data to a file."""
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get(self, src: str) -> dict:
        """Load JSON data from a file."""
        if not (exists(src) and isfile(src)):
            return {}

        with open(src, encoding="utf-8") as f:
            return json.load(f)
