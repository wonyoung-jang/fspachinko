"""Actions module for QActions."""

from dataclasses import dataclass, field

from PySide6.QtGui import QAction, QIcon

from ..utils import IconFilename, Paths
from .components import set_qt_tips

i_save = QIcon(Paths.icon(IconFilename.SAVE))
i_save_as = QIcon(Paths.icon(IconFilename.SAVE_AS))
i_open = QIcon(Paths.icon(IconFilename.OPEN))
i_autosave = QIcon(Paths.icon(IconFilename.AUTOSAVE))
i_start = QIcon(Paths.icon(IconFilename.START))
i_stop = QIcon(Paths.icon(IconFilename.STOP))
i_close = QIcon(Paths.icon(IconFilename.CLOSE))


@dataclass(slots=True)
class FileActions:
    """Main file menu actions for File Roulette."""

    save: QAction = field(init=False)
    save_as: QAction = field(init=False)
    load: QAction = field(init=False)
    autosave: QAction = field(init=False)
    exit: QAction = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the main actions."""
        self.save = QAction(icon=i_save, text="&Save Profile")
        self.save.setShortcut("Ctrl+S")
        set_qt_tips(self.save, "Save current GUI profile (Ctrl+S)")

        self.save_as = QAction(icon=i_save_as, text="Save Profile &As")
        self.save_as.setShortcut("Ctrl+Shift+S")
        set_qt_tips(self.save_as, "Save current GUI profile as ... (Ctrl+Shift+S)")

        self.load = QAction(icon=i_open, text="&Load Profile")
        self.load.setShortcut("Ctrl+O")
        set_qt_tips(self.load, "Load GUI profile (Ctrl+O)")

        self.autosave = QAction(icon=i_autosave, text="A&utosave Profile", checkable=True, checked=True)
        set_qt_tips(self.autosave, "Automatically save profile on exit")

        self.exit = QAction(icon=i_close, text="&Exit")
        self.exit.setShortcut("Ctrl+W")
        set_qt_tips(self.exit, "Exit application (Ctrl+W)")


@dataclass(slots=True)
class RunActions:
    """Main run actions for File Roulette."""

    start: QAction = field(init=False)
    stop: QAction = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the main actions."""
        self.start = QAction(icon=i_start, text="&Start")
        self.start.setShortcut("Ctrl+R")
        set_qt_tips(self.start, "Start (Ctrl+R)")

        self.stop = QAction(icon=i_stop, text="S&top")
        self.stop.setShortcut("ESC")
        set_qt_tips(self.stop, "Stop (ESC)")


@dataclass(slots=True)
class FileRouletteActions:
    """Main actions for File Roulette."""

    file: FileActions = field(default_factory=FileActions)
    run: RunActions = field(default_factory=RunActions)
