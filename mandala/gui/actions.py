"""Actions module for QActions."""

from dataclasses import dataclass, field

from PySide6.QtGui import QAction, QIcon, QKeySequence

from ..utils.constants import ICONS_DIR
from .components import set_qt_tips

save_icon = str(ICONS_DIR / "save_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg")
save_as_icon = str(ICONS_DIR / "save_as_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg")
open_icon = str(ICONS_DIR / "file_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg")
autosave_icon = str(ICONS_DIR / "sync_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg")
start_icon = str(ICONS_DIR / "play_arrow_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg")
stop_icon = str(ICONS_DIR / "stop_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg")
close_icon = str(ICONS_DIR / "close_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg")


@dataclass(slots=True)
class FileActions:
    """Main file menu actions for Mandala."""

    save: QAction = field(init=False)
    save_as: QAction = field(init=False)
    load: QAction = field(init=False)
    autosave: QAction = field(init=False)
    exit: QAction = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the main actions."""
        self.save = QAction(icon=QIcon(save_icon), text="&Save Profile", shortcut=QKeySequence.fromString("Ctrl+S"))
        set_qt_tips(self.save, "Save current GUI profile (Ctrl+S)")

        self.save_as = QAction(
            icon=QIcon(save_as_icon), text="Save Profile &As", shortcut=QKeySequence.fromString("Ctrl+Shift+S")
        )
        set_qt_tips(self.save_as, "Save current GUI profile as ... (Ctrl+Shift+S)")

        self.load = QAction(icon=QIcon(open_icon), text="&Load Profile", shortcut=QKeySequence.fromString("Ctrl+O"))
        set_qt_tips(self.load, "Load GUI profile (Ctrl+O)")

        self.autosave = QAction(icon=QIcon(autosave_icon), text="A&utosave Profile", checkable=True, checked=True)
        set_qt_tips(self.autosave, "Automatically save profile on exit")

        self.exit = QAction(icon=QIcon(close_icon), text="&Exit", shortcut=QKeySequence.fromString("Ctrl+W"))
        set_qt_tips(self.exit, "Exit application (Ctrl+W)")


@dataclass(slots=True)
class RunActions:
    """Main run actions for Mandala."""

    start: QAction = field(init=False)
    stop: QAction = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the main actions."""
        self.start = QAction(icon=QIcon(start_icon), text="&Start", shortcut=QKeySequence.fromString("Ctrl+R"))
        set_qt_tips(self.start, "Start (Ctrl+R)")

        self.stop = QAction(icon=QIcon(stop_icon), text="S&top", shortcut=QKeySequence.fromString("ESC"))
        set_qt_tips(self.stop, "Stop (ESC)")


@dataclass(slots=True)
class MandalaActions:
    """Main actions for Mandala."""

    file: FileActions = field(default_factory=FileActions)
    run: RunActions = field(default_factory=RunActions)
