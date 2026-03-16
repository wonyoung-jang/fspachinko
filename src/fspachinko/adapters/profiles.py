"""Settings handling."""

from dataclasses import dataclass
from os.path import dirname

from .filesystemport import get_profile_path
from .jsonport import load_json, save_json


@dataclass(slots=True)
class ProfileManager:
    """Class for managing configuration profiles."""

    _path: str = ""

    @property
    def path(self) -> str:
        """Get the current profile path."""
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        """Set the current profile path."""
        self._path = get_profile_path(value)

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
