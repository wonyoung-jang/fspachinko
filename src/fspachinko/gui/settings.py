"""Settings handling for GUI."""

import json
from dataclasses import dataclass
from os.path import dirname, exists, isfile
from typing import TYPE_CHECKING

from ..adapters.datapaths import get_profile_path
from .qthelpers import get_widget_value, iter_custom_widget, set_widget_value

if TYPE_CHECKING:
    from collections.abc import Iterator

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
        data = dict(self.set_generator(parent))
        save_json(self.path, data, sort=True)

    def get(self, parent: QWidget) -> None:
        """Recursively load settings for all child widgets."""
        data = load_json(self.path)
        for child, val in self.get_generator(parent, data):
            set_widget_value(child, val)

    def set_generator(self, parent: QWidget) -> Iterator[tuple[str, object]]:
        """Recursively save settings for all child widgets."""
        for key, child in iter_custom_widget(parent):
            if (val := get_widget_value(child)) is not None:
                yield key, val

    def get_generator(self, parent: QWidget, data: dict) -> Iterator[tuple[QWidget, object]]:
        """Recursively load settings for all child widgets."""
        for key, child in iter_custom_widget(parent):
            if (val := data.get(key)) is not None:
                yield child, val


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
