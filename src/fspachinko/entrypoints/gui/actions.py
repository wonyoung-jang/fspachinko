"""Actions module for QActions."""

from dataclasses import dataclass

from PySide6.QtGui import QAction, QIcon, QKeySequence

from fspachinko.adapters.filesystemport import get_icon_path
from fspachinko.constants import IconFilename

from .qthelpers import set_qt_tips


def build_action(icon: str, text: str, shortcut: str, tip: str) -> QAction:
    """Build a QAction."""
    action = QAction(icon=QIcon(get_icon_path(icon)), text=text, shortcut=QKeySequence.fromString(shortcut))
    set_qt_tips(action, tip)
    return action


ACTION_CONFIG = {
    "save": (IconFilename.SAVE, "&Save Profile", "Ctrl+S", "Save current profile (Ctrl+S)"),
    "save_as": (IconFilename.SAVE_AS, "Save Profile &As", "Ctrl+Shift+S", "Save current profile as ... (Ctrl+Shift+S)"),
    "load": (IconFilename.OPEN, "&Load Profile", "Ctrl+O", "Load profile (Ctrl+O)"),
    "exit": (IconFilename.CLOSE, "&Exit", "Ctrl+W", "Exit application (Ctrl+W)"),
    "start": (IconFilename.START, "&Start", "Ctrl+R", "Start (Ctrl+R)"),
    "stop": (IconFilename.STOP, "S&top", "ESC", "Stop (ESC)"),
}


def get_actions() -> Actions:
    """Get file menu actions."""
    actions = {k: build_action(*v) for k, v in ACTION_CONFIG.items()}
    return Actions(**actions)


@dataclass(slots=True)
class Actions:
    """Main file menu actions."""

    save: QAction
    save_as: QAction
    load: QAction
    exit: QAction
    start: QAction
    stop: QAction
