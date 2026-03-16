"""Settings handling."""

import json
from dataclasses import dataclass
from os.path import dirname, exists, isfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(slots=True)
class ProfileManager:
    """Class for managing configuration profiles."""

    path_setter_fn: Callable[[str], str]
    _path: str = ""

    @property
    def path(self) -> str:
        """Get the current profile path."""
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        """Set the current profile path."""
        self._path = self.path_setter_fn(value)

    @property
    def parent(self) -> str:
        """Get the parent directory of the current profile."""
        return dirname(self.path)

    def set(self, data: dict) -> None:
        """Save configuration from a dict to the profile path."""
        save_json(self.path, data)

    def get(self) -> dict:
        """Load configuration from the profile path and return as a dict."""
        return load_json(self.path)


def save_json(path: str, data: dict, *, sort: bool = False) -> None:
    """Save JSON data to a file."""
    with open(path, "w", encoding="utf-8") as f:
        if sort:
            data = dict(sorted(data.items(), key=lambda x: x[0]))
        json.dump(data, f, indent=4)


def load_json(path: str) -> dict:
    """Load JSON data from a file."""
    if not (exists(path) and isfile(path)):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)
