"""Settings handling for Mandala GUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QByteArray, QCoreApplication, QSettings
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

    def save_gui(self) -> None:
        """Save the state of all registered widgets."""
        for name, widget in self.registry.items():
            if (val := self.get_widget_value(widget)) is not None:
                self.settings.setValue(name, val)

            if isinstance(widget, QComboBox):
                items = [widget.itemText(i) for i in range(widget.count())]
                self.settings.setValue(f"{name}_items", items)

    def load_gui(self) -> None:
        """Load the state of all registered widgets."""
        for name, widget in self.registry.items():
            if isinstance(widget, QComboBox):
                items = self.settings.value(f"{name}_items")
                if isinstance(items, list | tuple):
                    widget.clear()
                    widget.addItems([str(i) for i in items])

            if (val := self.settings.value(name)) is not None:
                self.set_widget_value(widget, val)

    def get_widget_value(self, widget: QWidget) -> Any:
        """Retrieve the value of a widget based on its type."""
        match widget:
            case QLineEdit():
                return widget.text()
            case QComboBox():
                return widget.currentIndex()
            case QSpinBox() | QDoubleSpinBox():
                return widget.value()
            case QCheckBox() | QRadioButton() | QGroupBox():
                if isinstance(widget, QGroupBox) and not widget.isCheckable():
                    return None
                return widget.isChecked()
        return None

    def set_widget_value(self, widget: QWidget, value: Any) -> None:
        """Set the value of a widget based on its type."""
        match widget:
            case QLineEdit():
                widget.setText(value)
            case QComboBox():
                try:
                    index = int(value)
                    if index >= widget.count():
                        index = 0
                    widget.setCurrentIndex(index)
                except (ValueError, TypeError):
                    pass
            case QSpinBox():
                widget.setValue(int(value))
            case QDoubleSpinBox():
                widget.setValue(float(value))
            case QCheckBox() | QRadioButton() | QGroupBox():
                state = strtobool(value) if isinstance(value, str) else bool(value)
                widget.setChecked(state)

    def get_window_settings(self) -> QByteArray:
        """Restore the geometry and state of the main window."""
        return self.settings.value("geometry")

    def save_window_settings(self, geometry: QByteArray) -> None:
        """Save the geometry and state of the main window."""
        self.settings.setValue("geometry", geometry)
