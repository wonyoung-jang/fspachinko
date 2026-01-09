"""Settings handling for Mandala GUI."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QByteArray, QCoreApplication, QSettings, Slot
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

from ..config.constants import SettingsEnum
from ..utilities.utils import strtobool

QCoreApplication.setOrganizationName(SettingsEnum.ORGANIZATION)
QCoreApplication.setOrganizationDomain(SettingsEnum.DOMAIN)
QCoreApplication.setApplicationName(SettingsEnum.APPLICATION)


@dataclass(slots=True)
class GuiSettingsManager:
    """Class for managing GUI settings."""

    settings: QSettings = field(init=False)
    registry: dict[str, QWidget] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        self.settings = QSettings()

    def register_widgets(self, widgets: dict[str, QWidget]) -> None:
        """Register multiple widgets for settings management."""
        self.registry.update(widgets)

    @Slot()
    def save_gui(self) -> None:
        """Save the state of all registered widgets."""
        for name, widget in self.registry.items():
            val = self.get_widget_value(widget)
            self.settings.setValue(name, val)
            if isinstance(widget, QComboBox):
                items = [widget.itemText(i) for i in range(widget.count())]
                self.settings.setValue(f"{name}_items", items)

    def get_widget_value(self, widget: QWidget) -> Any:
        """Retrieve the value of a widget based on its type."""
        if isinstance(widget, QLineEdit):
            return widget.text()
        if isinstance(widget, QComboBox):
            return widget.currentIndex()
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            return widget.value()
        if isinstance(widget, (QCheckBox, QRadioButton, QGroupBox)):
            if isinstance(widget, QGroupBox) and not widget.isCheckable():
                return None
            return widget.isChecked()
        return None

    @Slot()
    def load_gui(self) -> None:
        """Load the state of all registered widgets."""
        for name, widget in self.registry.items():
            if not self.settings.contains(name):
                continue

            val = self.settings.value(name)
            if val is None:
                continue

            self.set_widget_value(widget, val)

    def set_widget_value(self, widget: QWidget, value: Any) -> None:
        """Set the value of a widget based on its type."""
        if isinstance(widget, QLineEdit):
            widget.setText(value)
        elif isinstance(widget, QComboBox):
            widget.setCurrentIndex(int(value))
            if isinstance(value, Sequence):
                widget.clear()
                widget.addItems(value)
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))
        elif isinstance(widget, (QCheckBox, QRadioButton, QGroupBox)):
            state = strtobool(value) if isinstance(value, str) else bool(value)
            widget.setChecked(state)

    def get_window_settings(self) -> tuple[QByteArray, bool]:
        """Restore the geometry and state of the main window."""
        geometry_val = self.settings.value("geometry")
        show_invalid_val = self.settings.value("show_invalid")
        return geometry_val, strtobool(show_invalid_val)

    def save_window_settings(self, geometry: QByteArray, *, show_invalid: bool) -> None:
        """Save the geometry and state of the main window."""
        self.settings.setValue("geometry", geometry)
        self.settings.setValue("show_invalid", show_invalid)
