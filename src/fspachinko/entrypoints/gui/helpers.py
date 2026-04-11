"""Helper functions for Qt GUI elements."""

from functools import cache
from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon, QKeySequence

from fspachinko.datapaths import get_icon_path

if TYPE_CHECKING:
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QWidget


def set_qt_tips(w: QWidget | QAction, tooltip: str, statustip: str = "") -> None:
    """Set the tooltip and status tip for a widget."""
    w.setToolTip(tooltip)
    w.setStatusTip(statustip or tooltip)


@cache
def get_qt_icon(name: str) -> QIcon:
    """Get cached icon by declarative name."""
    if filename := {
        "window": "windowIcon.png",
        "browse": "folder_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        "open_dir": "open_in_new_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        "save": "save_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        "save_as": "save_as_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        "load": "file_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        "exit": "close_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        "start": "play_arrow_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
        "stop": "stop_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    }.get(name):
        return QIcon(get_icon_path(filename))
    msg = f"Unknown icon: {name}"
    raise ValueError(msg)


@cache
def get_qt_shortcut(name: str) -> QKeySequence:
    """Get cached shortcut by declarative name."""
    if seq := {
        "save": "Ctrl+S",
        "save_as": "Ctrl+Shift+S",
        "load": "Ctrl+O",
        "exit": "Ctrl+W",
        "start": "Ctrl+R",
        "stop": "ESC",
    }.get(name):
        return QKeySequence(seq)
    msg = f"Unknown shortcut: {name}"
    raise ValueError(msg)
