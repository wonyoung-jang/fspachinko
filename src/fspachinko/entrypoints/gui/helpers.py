"""Helper functions for Qt GUI elements."""

from functools import cache
from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon, QKeySequence

from fspachinko.datapaths import get_icon_path
from fspachinko.entrypoints.gui.constants import ICON_CONFIG, SHORTCUT_CONFIG

if TYPE_CHECKING:
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QWidget


def set_qt_tips(w: QWidget | QAction, tooltip: str, statustip: str = "") -> None:
    """Set the tooltip and status tip for a widget."""
    if not statustip:
        statustip = f"{tooltip} | ({w.metaObject().className()})"
    w.setToolTip(tooltip)
    w.setStatusTip(statustip)


@cache
def get_qt_icon(name: str) -> QIcon:
    """Get cached icon by declarative name."""
    if filename := ICON_CONFIG.get(name):
        return QIcon(get_icon_path(filename))
    msg = f"Unknown icon: {name}"
    raise ValueError(msg)


@cache
def get_qt_shortcut(name: str) -> QKeySequence:
    """Get cached shortcut by declarative name."""
    if seq := SHORTCUT_CONFIG.get(name):
        return QKeySequence(seq)
    msg = f"Unknown shortcut: {name}"
    raise ValueError(msg)
