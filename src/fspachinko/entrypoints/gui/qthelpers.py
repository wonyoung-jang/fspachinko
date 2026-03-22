"""Helper functions for Qt GUI elements."""

from functools import cache
from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon, QKeySequence

from fspachinko.adapters.filesystemport import get_icon_path

from .constants_gui import GUIIconFilename

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
def window_icon() -> QIcon:
    """Get the window icon."""
    return QIcon(get_icon_path(GUIIconFilename.WINDOW))


@cache
def save_icon() -> QIcon:
    """Get the save icon."""
    return QIcon(get_icon_path(GUIIconFilename.SAVE))


@cache
def save_as_icon() -> QIcon:
    """Get the save as icon."""
    return QIcon(get_icon_path(GUIIconFilename.SAVE_AS))


@cache
def load_icon() -> QIcon:
    """Get the load icon."""
    return QIcon(get_icon_path(GUIIconFilename.OPEN))


@cache
def exit_icon() -> QIcon:
    """Get the exit icon."""
    return QIcon(get_icon_path(GUIIconFilename.CLOSE))


@cache
def start_icon() -> QIcon:
    """Get the start icon."""
    return QIcon(get_icon_path(GUIIconFilename.START))


@cache
def stop_icon() -> QIcon:
    """Get the stop icon."""
    return QIcon(get_icon_path(GUIIconFilename.STOP))


@cache
def browse_icon() -> QIcon:
    """Get the browse icon."""
    return QIcon(get_icon_path(GUIIconFilename.BROWSE))


@cache
def open_dir_icon() -> QIcon:
    """Get the open directory icon."""
    return QIcon(get_icon_path(GUIIconFilename.OPEN_DIR))


@cache
def save_shortcut() -> QKeySequence:
    """Get the save shortcut."""
    return QKeySequence("Ctrl+S")


@cache
def save_as_shortcut() -> QKeySequence:
    """Get the save as shortcut."""
    return QKeySequence("Ctrl+Shift+S")


@cache
def load_shortcut() -> QKeySequence:
    """Get the load shortcut."""
    return QKeySequence("Ctrl+O")


@cache
def exit_shortcut() -> QKeySequence:
    """Get the exit shortcut."""
    return QKeySequence("Ctrl+W")


@cache
def start_shortcut() -> QKeySequence:
    """Get the start shortcut."""
    return QKeySequence("Ctrl+R")


@cache
def stop_shortcut() -> QKeySequence:
    """Get the stop shortcut."""
    return QKeySequence("ESC")


GUI_ACTION_CONFIG = {
    "save": (save_icon, "&Save Profile", save_shortcut, "Save current profile (Ctrl+S)"),
    "save_as": (save_as_icon, "Save Profile &As", save_as_shortcut, "Save current profile as ... (Ctrl+Shift+S)"),
    "load": (load_icon, "&Load Profile", load_shortcut, "Load profile (Ctrl+O)"),
    "exit": (exit_icon, "&Exit", exit_shortcut, "Exit application (Ctrl+W)"),
    "start": (start_icon, "&Start", start_shortcut, "Start (Ctrl+R)"),
    "stop": (stop_icon, "S&top", stop_shortcut, "Stop (ESC)"),
}
