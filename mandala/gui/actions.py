"""Actions module for QActions."""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtGui import QAction, QKeySequence


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
        self.save = QAction(
            "&Save Profile",
            statusTip="Save the current GUI profile (Ctrl+S)",
            shortcut=QKeySequence.fromString("Ctrl+S"),
        )
        self.save_as = QAction(
            "Save Profile &As",
            statusTip="Save the current GUI profile as ... (Ctrl+Shift+S)",
            shortcut=QKeySequence.fromString("Ctrl+Shift+S"),
        )
        self.load = QAction(
            "&Load Profile",
            statusTip="Load a GUI profile (Ctrl+O)",
            shortcut=QKeySequence.fromString("Ctrl+O"),
        )
        self.autosave = QAction(
            "A&utosave Profile",
            checkable=True,
            checked=True,
            statusTip="Automatically save the profile on exit",
        )
        self.exit = QAction(
            "&Exit",
            statusTip="Exit the application (Ctrl+W)",
            shortcut=QKeySequence.fromString("Ctrl+W"),
        )


@dataclass(slots=True)
class RunActions:
    """Main run actions for Mandala."""

    start: QAction = field(init=False)
    stop: QAction = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the main actions."""
        self.start = QAction(
            "&Start",
            statusTip="Start the file copying process (Ctrl+R)",
            shortcut=QKeySequence.fromString("Ctrl+R"),
        )
        self.stop = QAction(
            "S&top",
            statusTip="Stop the file copying process (ESC)",
            shortcut=QKeySequence.fromString("ESC"),
        )


@dataclass(slots=True)
class MandalaActions:
    """Main actions for Mandala."""

    file: FileActions = field(default_factory=FileActions)
    run: RunActions = field(default_factory=RunActions)
