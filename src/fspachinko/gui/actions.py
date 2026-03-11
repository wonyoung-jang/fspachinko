"""Actions module for QActions."""

from dataclasses import dataclass, field

from PySide6.QtGui import QAction, QIcon, QKeySequence

from ..adapters.datapaths import get_icon_path
from ..constants import IconFilename
from .qthelpers import set_qt_tips


class FileActions:
    """Main file menu actions."""

    def __init__(self) -> None:
        """Initialize the main actions."""
        self.save = QAction(
            icon=QIcon(get_icon_path(IconFilename.SAVE)),
            text="&Save Profile",
            shortcut=QKeySequence.fromString("Ctrl+S"),
        )
        self.save_as = QAction(
            icon=QIcon(get_icon_path(IconFilename.SAVE_AS)),
            text="Save Profile &As",
            shortcut=QKeySequence.fromString("Ctrl+Shift+S"),
        )
        self.load = QAction(
            icon=QIcon(get_icon_path(IconFilename.OPEN)),
            text="&Load Profile",
            shortcut=QKeySequence.fromString("Ctrl+O"),
        )
        self.autosave = QAction(
            icon=QIcon(get_icon_path(IconFilename.AUTOSAVE)),
            text="A&utosave Profile",
            shortcut=QKeySequence.fromString("Ctrl+U"),
            checkable=True,
            checked=True,
        )
        self.exit = QAction(
            icon=QIcon(get_icon_path(IconFilename.CLOSE)),
            text="&Exit",
            shortcut=QKeySequence.fromString("Ctrl+W"),
        )
        set_qt_tips(self.save, "Save current GUI profile (Ctrl+S)")
        set_qt_tips(self.save_as, "Save current GUI profile as ... (Ctrl+Shift+S)")
        set_qt_tips(self.load, "Load GUI profile (Ctrl+O)")
        set_qt_tips(self.autosave, "Automatically save profile on exit")
        set_qt_tips(self.exit, "Exit application (Ctrl+W)")


class RunActions:
    """Main run actions."""

    def __init__(self) -> None:
        """Initialize the main actions."""
        self.start = QAction(
            icon=QIcon(get_icon_path(IconFilename.START)),
            text="&Start",
            shortcut=QKeySequence.fromString("Ctrl+R"),
        )
        self.stop = QAction(
            icon=QIcon(get_icon_path(IconFilename.STOP)),
            text="S&top",
            shortcut=QKeySequence.fromString("ESC"),
        )
        set_qt_tips(self.start, "Start (Ctrl+R)")
        set_qt_tips(self.stop, "Stop (ESC)")


@dataclass(slots=True)
class Actions:
    """Main actions."""

    file: FileActions = field(default_factory=FileActions)
    run: RunActions = field(default_factory=RunActions)
