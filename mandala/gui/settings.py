"""Settings handling for Mandala GUI."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QLineEdit,
    QRadioButton,
    QSpinBox,
    QWidget,
)

from ..utils import PROFILES_DIR, AppSettings, strtobool

if TYPE_CHECKING:
    from collections.abc import Iterator

QCoreApplication.setOrganizationName(AppSettings.ORGANIZATION)
QCoreApplication.setOrganizationDomain(AppSettings.DOMAIN)
QCoreApplication.setApplicationName(AppSettings.APPLICATION)


def get_widget_value(widget: QWidget) -> Any:
    """Retrieve the value of a widget based on its type.

    Args:
        widget (QWidget): The widget to retrieve the value from.

    Returns:
        Any: The value of the widget, or None if not applicable.

    """
    match widget:
        case QLineEdit():
            return widget.text()
        case QComboBox():
            return widget.currentIndex()
        case QSpinBox() | QDoubleSpinBox():
            return widget.value()
        case QGroupBox() if not widget.isCheckable():
            return None
        case QCheckBox() | QRadioButton() | QGroupBox():
            return widget.isChecked()
        case _:
            return None


def set_widget_value(widget: QWidget, val: Any) -> None:
    """Set the value of a widget based on its type."""
    match widget:
        case QLineEdit():
            widget.setText(val)
        case QComboBox():
            try:
                index = int(val)
                if 0 <= index < widget.count():
                    widget.setCurrentIndex(index)
            except (ValueError, TypeError):
                pass
        case QSpinBox():
            widget.setValue(int(val))
        case QDoubleSpinBox():
            widget.setValue(float(val))
        case QCheckBox() | QRadioButton() | QGroupBox():
            state = strtobool(val=val)
            widget.setChecked(state)
        case _:
            return


def _iter_valid_widgets(w: QWidget) -> Iterator[tuple[str, QWidget]]:
    """Iterate over valid child widgets."""
    for child in w.findChildren(QWidget):
        if (key := child.objectName()) and not key.startswith("qt_"):
            yield key, child


@dataclass(slots=True)
class ProfileManager:
    """Class for managing GUI profiles."""

    profile_dir: Path = PROFILES_DIR
    current_profile: Path = field(init=False)

    def set_current(self, profile: str) -> None:
        """Set the current profile name."""
        self.current_profile = Path(profile)

    def _get_profile_path(self) -> Path:
        """Get the full path for a given profile name."""
        return self.profile_dir / self.current_profile

    def save_profile(self, parent: QWidget) -> None:
        """Recursively save settings for all child widgets."""
        data = {}
        for key, child in _iter_valid_widgets(parent):
            if (val := get_widget_value(child)) is not None:
                data[key] = val

                if isinstance(child, QComboBox):
                    items = [child.itemText(i) for i in range(child.count())]
                    data[f"{key}_items"] = items

        path = self._get_profile_path()
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def open_profile(self, parent: QWidget) -> None:
        """Recursively load settings for all child widgets."""
        path = self._get_profile_path()
        if not (path.exists() and path.is_file()):
            return

        data = {}
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        for key, child in _iter_valid_widgets(parent):
            if isinstance(child, QComboBox) and (items := data.get(f"{key}_items")) and isinstance(items, list | tuple):
                child.clear()
                child.addItems([str(i) for i in items])

            if (val := data.get(key)) is not None:
                set_widget_value(child, val)
