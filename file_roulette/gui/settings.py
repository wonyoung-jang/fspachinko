"""Settings handling for File Roulette GUI."""

import os
from collections.abc import Sequence
from dataclasses import dataclass, field

from PySide6.QtWidgets import QComboBox, QWidget

from ..utils import Paths, load_json, save_json
from .qthelpers import get_widget_value, iter_custom_widget, set_widget_value


@dataclass(slots=True)
class ProfileManager:
    """Class for managing GUI profiles."""

    current_profile: str = field(init=False)

    def set_current(self, profile: str) -> None:
        """Set the current profile name."""
        self.current_profile = Paths.profile(profile)

    def save_profile(self, parent: QWidget) -> None:
        """Recursively save settings for all child widgets."""
        data = {}
        for key, child in iter_custom_widget(parent):
            if (val := get_widget_value(child)) is None:
                continue

            data[key] = val
            if isinstance(child, QComboBox):
                items = [child.itemText(i) for i in range(child.count())]
                data[f"{key}_items"] = items

        save_json(self.current_profile, data)

    def open_profile(self, parent: QWidget) -> None:
        """Recursively load settings for all child widgets."""
        data = load_json(self.current_profile)

        for key, child in iter_custom_widget(parent):
            if isinstance(child, QComboBox):
                items = data.get(f"{key}_items")
                if isinstance(items, Sequence):
                    child.clear()
                    child.addItems([str(i) for i in items])

            if (val := data.get(key)) is not None:
                set_widget_value(child, val)

    def get_current_profile_parent(self) -> str:
        """Get the parent directory of the current profile."""
        return os.path.dirname(self.current_profile)
