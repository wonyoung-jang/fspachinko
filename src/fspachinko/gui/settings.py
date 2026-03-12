"""Settings handling for GUI."""

from dataclasses import dataclass
from os.path import dirname
from typing import TYPE_CHECKING

from ..adapters.datapaths import get_profile_path
from ..adapters.jsonport import load_json, save_json
from .qthelpers import get_widget_value, iter_custom_widget, set_widget_value

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


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

    def set(self, parent: QWidget) -> None:
        """Recursively save settings for all child widgets."""
        data = {}
        for key, child in iter_custom_widget(parent):
            if (val := get_widget_value(child)) is not None:
                data[key] = val
        save_json(self.path, data, sort=True)

    def get(self, parent: QWidget) -> None:
        """Recursively load settings for all child widgets."""
        data = load_json(self.path)
        for key, child in iter_custom_widget(parent):
            if (val := data.get(key)) is not None:
                set_widget_value(child, val)
