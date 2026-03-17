"""Actions module for QActions."""

from dataclasses import dataclass

from PySide6.QtGui import QAction

from .qthelpers import exit_icon, load_icon, save_as_icon, save_icon, set_qt_tips, start_icon, stop_icon


@dataclass(slots=True)
class Actions:
    """Main file menu actions."""

    save: QAction
    save_as: QAction
    load: QAction
    exit: QAction
    start: QAction
    stop: QAction


ACTION_CONFIG = {
    "save": (save_icon, "&Save Profile", "Ctrl+S", "Save current profile (Ctrl+S)"),
    "save_as": (save_as_icon, "Save Profile &As", "Ctrl+Shift+S", "Save current profile as ... (Ctrl+Shift+S)"),
    "load": (load_icon, "&Load Profile", "Ctrl+O", "Load profile (Ctrl+O)"),
    "exit": (exit_icon, "&Exit", "Ctrl+W", "Exit application (Ctrl+W)"),
    "start": (start_icon, "&Start", "Ctrl+R", "Start (Ctrl+R)"),
    "stop": (stop_icon, "S&top", "ESC", "Stop (ESC)"),
}


def get_actions() -> Actions:
    """Get file menu actions."""
    actions = {}
    for k, v in ACTION_CONFIG.items():
        icon, text, shortcut, tip = v
        actions[k] = QAction(icon(), text)
        actions[k].setShortcut(shortcut)
        set_qt_tips(actions[k], tip)
    return Actions(**actions)
