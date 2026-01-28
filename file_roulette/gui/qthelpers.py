"""Helper functions for Qt GUI elements."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import QObject
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QWidget


def get_qt_classname(obj: QObject) -> str:
    """Get the class name of a QObject."""
    return str(obj.metaObject().className())


def set_qt_name(w: QWidget | QAction, name: str) -> None:
    """Initialize a widget with a given object name."""
    w.setObjectName(name)


def set_qt_tips(w: QWidget | QAction, tooltip: str, statustip: str = "") -> None:
    """Set the tooltip and status tip for a widget."""
    if not statustip:
        statustip = f"{tooltip} | ({get_qt_classname(w)})"

    w.setToolTip(tooltip)
    w.setStatusTip(statustip)
