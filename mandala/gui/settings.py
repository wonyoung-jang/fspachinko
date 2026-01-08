"""Settings handling for Mandala GUI."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QSettings, Slot
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


@dataclass(slots=True)
class GuiSettingsManager:
    """Class for managing GUI settings."""

    settings: QSettings = field(default_factory=QSettings)
    registry: dict[str, QWidget] = field(default_factory=dict)

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
            if isinstance(value, Sequence[str]):
                widget.clear()
                widget.addItems(value)
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.setValue(value)
        elif isinstance(widget, (QCheckBox, QRadioButton, QGroupBox)):
            widget.setChecked(bool(value))
