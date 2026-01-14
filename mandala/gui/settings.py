"""Settings handling for Mandala GUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QLineEdit,
    QMainWindow,
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

    prefix: str
    settings: QSettings = field(default_factory=QSettings)

    def save(self, window: QMainWindow) -> None:
        """Save the state of all registered widgets."""
        self.save_window_state(window)
        self.save_children_recursive(window)

    def load(self, window: QMainWindow) -> None:
        """Load the state of all registered widgets."""
        self.load_window_state(window)
        self.load_children_recursive(window)

    def load_window_state(self, window: QMainWindow) -> None:
        """Restore the geometry and state of the main window."""
        window.restoreGeometry(self.settings.value(f"{self.prefix}/geometry"))
        window.restoreState(self.settings.value(f"{self.prefix}/state"))

    def save_window_state(self, window: QMainWindow) -> None:
        """Save the geometry and state of the main window."""
        self.settings.setValue(f"{self.prefix}/geometry", window.saveGeometry())
        self.settings.setValue(f"{self.prefix}/state", window.saveState())

    def save_children_recursive(self, parent: QWidget) -> None:
        """Recursively save settings for all child widgets."""
        for child in parent.findChildren(QWidget):
            if not child.objectName():
                continue

            val = self.get_widget_value(child)
            if val is not None:
                key = f"{self.prefix}/{child.objectName()}"
                self.settings.setValue(key, val)

                if isinstance(child, QComboBox):
                    items = [child.itemText(i) for i in range(child.count())]
                    self.settings.setValue(f"{key}_items", items)

    def load_children_recursive(self, parent: QWidget) -> None:
        """Recursively load settings for all child widgets."""
        for child in parent.findChildren(QWidget):
            if not child.objectName():
                continue

            key = f"{self.prefix}/{child.objectName()}"

            if (
                isinstance(child, QComboBox)
                and (items := self.settings.value(f"{key}_items"))
                and isinstance(items, (list, tuple))
            ):
                child.clear()
                child.addItems([str(i) for i in items])

            if (val := self.settings.value(key)) is not None:
                self.set_widget_value(child, val)

    def get_widget_value(self, widget: QWidget) -> Any:
        """Retrieve the value of a widget based on its type."""
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

    def set_widget_value(self, widget: QWidget, val: Any) -> None:
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
                state = strtobool(val) if isinstance(val, str) else bool(val)
                widget.setChecked(state)
            case _:
                return
