"""Settings handling for GUI."""

from dataclasses import dataclass
from os.path import dirname
from typing import TYPE_CHECKING

from ..adapters.filesystemport import get_profile_path
from ..adapters.jsonport import load_json, save_json

if TYPE_CHECKING:
    from .uibuilder import UIBuilder


@dataclass(slots=True)
class ProfileManager:
    """Class for managing GUI profiles."""

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

    def set(self, ui: UIBuilder) -> None:
        """Set the profile path from a UIBuilder instance."""
        data = ui.config
        save_json(self.path, data)

    def get(self, ui: UIBuilder) -> None:
        """Load the profile to a UIBuilder instance."""
        data = load_json(self.path)
        for component in ui.has_config:
            component.restore(data)
