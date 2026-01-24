"""Helper functions for Qt GUI elements."""

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


def set_widget_tips(w: QWidget, tip: str) -> None:
    """Set the tooltip and status tip for a widget."""
    w.setToolTip(tip)
    w.setStatusTip(f"{tip} | ({get_classname(w)})")
