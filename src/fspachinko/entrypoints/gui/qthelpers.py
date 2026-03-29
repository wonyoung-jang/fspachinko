"""Helper functions for Qt GUI elements."""

from functools import cache
from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon, QKeySequence

from fspachinko.datapaths import get_icon_path
from fspachinko.entrypoints.gui.constants_gui import GUIIconFilename, GUILabel, GUIName

if TYPE_CHECKING:
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QMainWindow, QMenu, QToolBar, QWidget

    from .components import Actions


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


def add_actions_to_bar(bar: QToolBar | QMenu, actions: Actions, actions_names: list[str | None]) -> None:
    """Add actions to a menu or toolbar based on a list of action keys."""
    for item in actions_names:
        if item is None:
            bar.addSeparator()
        else:
            action = getattr(actions, item)
            bar.addAction(action)


def build_ui_bars(window: QMainWindow, actions: Actions) -> None:
    """Build the status, tool, and menu bars."""
    statusbar = window.statusBar()
    statusbar.setSizeGripEnabled(True)
    toolbar = window.addToolBar(GUIName.TOOLBAR)
    toolbar.setObjectName(GUIName.TOOLBAR)
    add_actions_to_bar(toolbar, actions, TOOLBAR_STRUCTURE)
    menubar = window.menuBar()
    for menu_name, action_keys in MENU_STRUCTURE.items():
        menu = menubar.addMenu(menu_name)
        add_actions_to_bar(menu, actions, action_keys)


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
