"""Helper functions for Qt GUI elements."""

from functools import cache
from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon, QKeySequence

from fspachinko.datapaths import get_icon_path
from fspachinko.entrypoints.gui.constants import GUIIconFilename, GUILabel

if TYPE_CHECKING:
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QWidget


def set_qt_tips(w: QWidget | QAction, tooltip: str, statustip: str = "") -> None:
    """Set the tooltip and status tip for a widget."""
    if not statustip:
        statustip = f"{tooltip} | ({w.metaObject().className()})"
    w.setToolTip(tooltip)
    w.setStatusTip(statustip)


MENU_STRUCTURE = {
    GUILabel.FILEMENU: ["save", "save_as", "load", None, "exit"],
    GUILabel.RUNMENU: ["start", "stop"],
}

TOOLBAR_STRUCTURE = ["save", "save_as", "load", None, "start", "stop", None, "exit"]

ICON_MAP = {
    "window": GUIIconFilename.WINDOW,
    "browse": GUIIconFilename.BROWSE,
    "open_dir": GUIIconFilename.OPEN_DIR,
    "save": GUIIconFilename.SAVE,
    "save_as": GUIIconFilename.SAVE_AS,
    "load": GUIIconFilename.OPEN,
    "exit": GUIIconFilename.CLOSE,
    "start": GUIIconFilename.START,
    "stop": GUIIconFilename.STOP,
}

SHORTCUT_MAP = {
    "save": "Ctrl+S",
    "save_as": "Ctrl+Shift+S",
    "load": "Ctrl+O",
    "exit": "Ctrl+W",
    "start": "Ctrl+R",
    "stop": "ESC",
}


@cache
def get_icon(name: str) -> QIcon:
    """Get cached icon by declarative name."""
    if filename := ICON_MAP.get(name):
        return QIcon(get_icon_path(filename))
    msg = f"Unknown icon: {name}"
    raise ValueError(msg)


@cache
def get_shortcut(name: str) -> QKeySequence:
    """Get cached shortcut by declarative name."""
    if seq := SHORTCUT_MAP.get(name):
        return QKeySequence(seq)
    msg = f"Unknown shortcut: {name}"
    raise ValueError(msg)
