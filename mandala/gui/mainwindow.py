"""Main module for Mandala."""

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Slot
from PySide6.QtWidgets import QFileDialog, QMainWindow, QStatusBar, QToolBar

from .actions import MandalaActions
from .centralwidget import MandalaCentralGui
from .qthelpers import set_qt_name
from .settings import ProfileManager

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MandalaMainWindow(QMainWindow):
    """Main application window for Mandala."""

    ui: MandalaCentralGui = field(default_factory=MandalaCentralGui)
    profiles: ProfileManager = field(default_factory=ProfileManager)
    qsettings: QSettings = field(default_factory=QSettings)
    _actions: MandalaActions = field(default_factory=MandalaActions)

    def __post_init__(self) -> None:
        """Initialize the main window."""
        super().__init__()

        logger.debug("Initializing GUI")
        self.setCentralWidget(self.ui)
        self.init_connections()
        self.init_menubar()
        self.init_toolbar()
        self.init_statusbar()
        self.init_settings()

    def init_connections(self) -> None:
        """Initialize connections."""
        self._actions.file.save.triggered.connect(self.save_profile)
        self._actions.file.save_as.triggered.connect(self.save_profile_as_dialog)
        self._actions.file.load.triggered.connect(self.open_profile_dialog)
        self._actions.file.exit.triggered.connect(self.close)

        self._actions.run.start.triggered.connect(self.ui.on_start)
        self._actions.run.stop.triggered.connect(self.ui.on_stop)

    def init_menubar(self) -> None:
        """Initialize the menu bar."""
        menubar = self.menuBar()
        set_qt_name(menubar, "MandalaMenuBar")

        file_menu = menubar.addMenu("&File")
        set_qt_name(file_menu, "MandalaFileMenu")

        file_menu.addAction(self._actions.file.save)
        file_menu.addAction(self._actions.file.save_as)
        file_menu.addAction(self._actions.file.load)
        file_menu.addSeparator()
        file_menu.addAction(self._actions.file.autosave)
        file_menu.addSeparator()
        file_menu.addAction(self._actions.file.exit)

        run_menu = menubar.addMenu("&Run")
        set_qt_name(run_menu, "MandalaRunMenu")

        run_menu.addAction(self._actions.run.start)
        run_menu.addAction(self._actions.run.stop)

    def init_toolbar(self) -> None:
        """Initialize the toolbar."""
        toolbar = QToolBar("MandalaToolBar")
        set_qt_name(toolbar, "MandalaToolBar")

        toolbar.addAction(self._actions.file.save)
        toolbar.addAction(self._actions.file.save_as)
        toolbar.addAction(self._actions.file.load)
        toolbar.addAction(self._actions.file.autosave)
        toolbar.addSeparator()
        toolbar.addAction(self._actions.run.start)
        toolbar.addAction(self._actions.run.stop)
        toolbar.addSeparator()
        toolbar.addAction(self._actions.file.exit)

        self.addToolBar(toolbar)

    def init_statusbar(self) -> None:
        """Initialize the status bar."""
        statusbar = QStatusBar(self, sizeGripEnabled=True)
        set_qt_name(statusbar, "MandalaStatusBar")

        self.setStatusBar(statusbar)

    def init_settings(self) -> None:
        """Initialize GUI settings manager."""
        self.restoreGeometry(self.qsettings.value("geometry"))
        self.restoreState(self.qsettings.value("state"))
        self.profiles.set_current(str(self.qsettings.value("profile", "")))
        self.profiles.open_profile(self)
        self.reset_window_title()

    @Slot()
    def save_profile(self) -> None:
        """Save the current GUI profile."""
        self.profiles.save_profile(self)

    @Slot()
    def save_profile_as_dialog(self) -> None:
        """Save a GUI profile via dialog."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Profile As", str(self.profiles.profile_dir), "JSON Files (*.json)"
        )
        if filename:
            self.profiles.set_current(filename)
            self.save_profile()
            self.reset_window_title()

    @Slot()
    def open_profile_dialog(self) -> None:
        """Load a GUI profile via dialog."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Profile", str(self.profiles.profile_dir), "JSON Files (*.json)"
        )
        if filename:
            self.profiles.set_current(filename)
            self.profiles.open_profile(self)
            self.reset_window_title()

    @Slot()
    def reset_window_title(self) -> None:
        """Update the window title based on the current profile."""
        stem, _ = os.path.splitext(os.path.basename(self.profiles.current_profile))
        self.setWindowTitle(f"{stem} - Mandala: Copy random files")

    def save_settings(self) -> None:
        """Save GUI settings on close."""
        self.qsettings.setValue("geometry", self.saveGeometry())
        self.qsettings.setValue("state", self.saveState())
        self.qsettings.setValue("profile", self.profiles.current_profile)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Handle window close event."""
        self.save_settings()
        if self._actions.file.autosave.isChecked():
            self.save_profile()
        super().closeEvent(event)
