"""Helper functions for Qt GUI elements."""

from enum import StrEnum
from functools import cache
from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon, QKeySequence

from fspachinko.datapaths import get_icon_path

if TYPE_CHECKING:
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QWidget


class Keys(StrEnum):
    """Declarative keys for icons and shortcuts."""

    WINDOW = "window"
    BROWSE = "browse"
    OPEN_DIR = "open_dir"


class QtActionKeys(StrEnum):
    """Declarative keys for icons and shortcuts."""

    SAVE = "save"
    SAVE_AS = "save_as"
    LOAD = "load"
    EXIT = "exit"
    START = "start"
    STOP = "stop"


QT_ICON_CONFIG: dict[str, str] = {
    Keys.WINDOW: "windowIcon.png",
    Keys.BROWSE: "folder_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    Keys.OPEN_DIR: "open_in_new_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    QtActionKeys.SAVE: "save_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    QtActionKeys.SAVE_AS: "save_as_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    QtActionKeys.LOAD: "file_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    QtActionKeys.EXIT: "close_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    QtActionKeys.START: "play_arrow_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
    QtActionKeys.STOP: "stop_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg",
}
QT_SHORTCUT_CONFIG: dict[str, str] = {
    QtActionKeys.SAVE: "Ctrl+S",
    QtActionKeys.SAVE_AS: "Ctrl+Shift+S",
    QtActionKeys.LOAD: "Ctrl+O",
    QtActionKeys.EXIT: "Ctrl+W",
    QtActionKeys.START: "Ctrl+R",
    QtActionKeys.STOP: "ESC",
}
QT_ACTION_CONFIG: dict[str, tuple[str, str]] = {
    QtActionKeys.SAVE: ("&Save Configuration", "Save current configuration (Ctrl+S)"),
    QtActionKeys.SAVE_AS: ("Save Configuration &As", "Save current configuration as ... (Ctrl+Shift+S)"),
    QtActionKeys.LOAD: ("&Load Configuration", "Load configuration (Ctrl+O)"),
    QtActionKeys.EXIT: ("&Exit", "Exit application (Ctrl+W)"),
    QtActionKeys.START: ("&Start", "Start (Ctrl+R)"),
    QtActionKeys.STOP: ("S&top", "Stop (ESC)"),
}


def set_qt_tips(w: QWidget | QAction, tooltip: str, statustip: str = "") -> None:
    """Set the tooltip and status tip for a widget."""
    w.setToolTip(tooltip)
    w.setStatusTip(statustip or tooltip)


@cache
def get_qt_icon(name: str) -> QIcon:
    """Get cached icon by declarative name."""
    if filename := QT_ICON_CONFIG.get(name):
        return QIcon(get_icon_path(filename))
    msg = f"Unknown icon: {name}"
    raise ValueError(msg)


@cache
def get_qt_shortcut(name: str) -> QKeySequence:
    """Get cached shortcut by declarative name."""
    if seq := QT_SHORTCUT_CONFIG.get(name):
        return QKeySequence(seq)
    msg = f"Unknown shortcut: {name}"
    raise ValueError(msg)
