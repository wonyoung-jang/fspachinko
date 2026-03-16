"""Helper functions for Qt GUI elements."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QWidget


def set_qt_tips(w: QWidget | QAction, tooltip: str, statustip: str = "") -> None:
    """Set the tooltip and status tip for a widget."""
    if not statustip:
        statustip = f"{tooltip} | ({w.metaObject().className()})"
    w.setToolTip(tooltip)
    w.setStatusTip(statustip)
