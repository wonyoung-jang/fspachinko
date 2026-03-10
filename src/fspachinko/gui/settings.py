"""Settings handling for GUI."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from os.path import dirname, exists, isfile

from PySide6.QtWidgets import QComboBox, QWidget

from ..adapters.datapaths import get_profile_path
from .qthelpers import get_widget_value, iter_custom_widget, set_widget_value


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
            if (val := get_widget_value(child)) is None:
                continue

            data[key] = val
            if isinstance(child, QComboBox):
                items = [child.itemText(i) for i in range(child.count())]
                data[f"{key}_items"] = items

        self._save(data)

    def get(self, parent: QWidget) -> None:
        """Recursively load settings for all child widgets."""
        if not self._check_exists():
            return

        data = self._load()

        for key, child in iter_custom_widget(parent):
            if isinstance(child, QComboBox):
                items = data.get(f"{key}_items")
                if isinstance(items, Sequence):
                    child.clear()
                    child.addItems([str(i) for i in items])

            if (val := data.get(key)) is not None:
                set_widget_value(child, val)

    def _save(self, data: dict) -> None:
        """Save the profile data to the file."""
        with open(self.path, "w", encoding="utf-8") as f:
            data = dict(sorted(data.items(), key=lambda x: x[0]))
            json.dump(data, f, indent=4)

    def _load(self) -> dict:
        """Load the profile data from the file."""
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _check_exists(self) -> bool:
        """Check if the profile file exists."""
        return exists(self.path) and isfile(self.path)
