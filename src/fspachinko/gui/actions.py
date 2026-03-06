"""Actions module for QActions."""

from dataclasses import dataclass, field

from PySide6.QtGui import QAction, QIcon

from ..constants import IconFilename
from ..datapaths import get_icon_path
from .qthelpers import set_qt_tips


@dataclass(slots=True)
class FileActions:
    """Main file menu actions."""

    save: QAction = field(init=False)
    save_as: QAction = field(init=False)
    load: QAction = field(init=False)
    autosave: QAction = field(init=False)
    exit: QAction = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the main actions."""
        self.save = QAction(icon=QIcon(get_icon_path(IconFilename.SAVE)), text="&Save Profile")
        self.save.setShortcut("Ctrl+S")
        set_qt_tips(self.save, "Save current GUI profile (Ctrl+S)")

        self.save_as = QAction(icon=QIcon(get_icon_path(IconFilename.SAVE_AS)), text="Save Profile &As")
        self.save_as.setShortcut("Ctrl+Shift+S")
        set_qt_tips(self.save_as, "Save current GUI profile as ... (Ctrl+Shift+S)")

        self.load = QAction(icon=QIcon(get_icon_path(IconFilename.OPEN)), text="&Load Profile")
        self.load.setShortcut("Ctrl+O")
        set_qt_tips(self.load, "Load GUI profile (Ctrl+O)")

        self.autosave = QAction(
            icon=QIcon(get_icon_path(IconFilename.AUTOSAVE)),
            text="A&utosave Profile",
            checkable=True,
            checked=True,
        )
        set_qt_tips(self.autosave, "Automatically save profile on exit")

        self.exit = QAction(icon=QIcon(get_icon_path(IconFilename.CLOSE)), text="&Exit")
        self.exit.setShortcut("Ctrl+W")
        set_qt_tips(self.exit, "Exit application (Ctrl+W)")


@dataclass(slots=True)
class RunActions:
    """Main run actions."""

    start: QAction = field(init=False)
    stop: QAction = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the main actions."""
        self.start = QAction(icon=QIcon(get_icon_path(IconFilename.START)), text="&Start")
        self.start.setShortcut("Ctrl+R")
        set_qt_tips(self.start, "Start (Ctrl+R)")

        self.stop = QAction(icon=QIcon(get_icon_path(IconFilename.STOP)), text="S&top")
        self.stop.setShortcut("ESC")
        set_qt_tips(self.stop, "Stop (ESC)")


@dataclass(slots=True)
class Actions:
    """Main actions."""

    file: FileActions = field(default_factory=FileActions)
    run: RunActions = field(default_factory=RunActions)
