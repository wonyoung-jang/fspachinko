"""Actions module for QActions."""

from dataclasses import dataclass, field

from PySide6.QtGui import QAction, QIcon, QKeySequence

from ..adapters.filesystemport import get_icon_path
from ..constants import IconFilename
from .qthelpers import set_qt_tips


def build_action(icon: str, text: str, shortcut: str, tip: str) -> QAction:
    """Build a QAction."""
    action = QAction(icon=QIcon(get_icon_path(icon)), text=text, shortcut=QKeySequence.fromString(shortcut))
    set_qt_tips(action, tip)
    return action


QACTION_CONFIGS = {
    "save": (IconFilename.SAVE, "&Save Profile", "Ctrl+S", "Save current profile (Ctrl+S)"),
    "save_as": (IconFilename.SAVE_AS, "Save Profile &As", "Ctrl+Shift+S", "Save current profile as ... (Ctrl+Shift+S)"),
    "load": (IconFilename.OPEN, "&Load Profile", "Ctrl+O", "Load profile (Ctrl+O)"),
    "exit": (IconFilename.CLOSE, "&Exit", "Ctrl+W", "Exit application (Ctrl+W)"),
    "start": (IconFilename.START, "&Start", "Ctrl+R", "Start (Ctrl+R)"),
    "stop": (IconFilename.STOP, "S&top", "ESC", "Stop (ESC)"),
}


@dataclass(slots=True)
class FileActions:
    """Main file menu actions."""

    save: QAction
    save_as: QAction
    load: QAction
    exit: QAction


@dataclass(slots=True)
class RunActions:
    """Main run actions."""

    start: QAction
    stop: QAction


@dataclass(slots=True)
class Actions:
    """Main actions."""

    file: FileActions = field(init=False)
    run: RunActions = field(init=False)

    def __post_init__(self) -> None:
        """Post-initialization to set up any additional state if needed."""
        actions = {k: build_action(*v) for k, v in QACTION_CONFIGS.items()}
        self.file = FileActions(actions["save"], actions["save_as"], actions["load"], actions["exit"])
        self.run = RunActions(actions["start"], actions["stop"])
