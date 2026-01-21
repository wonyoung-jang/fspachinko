"""Helper functions for Qt GUI elements."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import QObject
    from PySide6.QtWidgets import QWidget


def get_classname(obj: QObject) -> str:
    """Get the class name of a QObject."""
    return str(obj.metaObject().className())


def init_widget(w: QWidget, name: str) -> None:
    """Initialize a widget with a given object name."""
    w.setObjectName(name)

    tooltip = f"{get_classname(w)}: {name}"
    w.setToolTip(tooltip)
