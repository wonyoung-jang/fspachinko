"""Main module for Mandala."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Slot
from PySide6.QtWidgets import QFileDialog, QMainWindow, QStatusBar, QToolBar

from .actions import MandalaActions
from .centralwidget import MandalaCentralGui
from .qthelpers import init_widget
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
        self.setCentralWidget(self.ui)
        self.ui.update_window_title.connect(self.update_window_title)

        logger.info("Initializing GUI")
        self.init_menubar()
        self.init_toolbar()
        self.init_statusbar()

        logger.info("Loading settings")
        self.init_settings()

    def init_menubar(self) -> None:
        """Initialize the menu bar."""
        menubar = self.menuBar()
        init_widget(menubar, "MandalaMenuBar")

        file_menu = menubar.addMenu("&File")
        init_widget(file_menu, "MandalaFileMenu")
        file_actions = self._actions.file
        file_menu.addAction(file_actions.save)
        file_menu.addAction(file_actions.save_as)
        file_menu.addAction(file_actions.load)
        file_menu.addSeparator()
        file_menu.addAction(file_actions.autosave)
        file_menu.addSeparator()
        file_menu.addAction(file_actions.exit)
        file_actions.save.triggered.connect(self.save_profile)
        file_actions.save_as.triggered.connect(self.save_profile_as_dialog)
        file_actions.load.triggered.connect(self.open_profile_dialog)
        file_actions.exit.triggered.connect(self.close)

        run_menu = menubar.addMenu("&Run")
        init_widget(run_menu, "MandalaRunMenu")
        run_actions = self._actions.run
        run_menu.addAction(run_actions.start)
        run_menu.addAction(run_actions.stop)
        run_actions.start.triggered.connect(self.ui.on_start)
        run_actions.stop.triggered.connect(self.ui.on_stop)

    def init_toolbar(self) -> None:
        """Initialize the toolbar."""
        toolbar = QToolBar("MandalaToolBar")
        init_widget(toolbar, "MandalaToolBar")
        file_actions = self._actions.file
        run_actions = self._actions.run
        toolbar.addAction(file_actions.save)
        toolbar.addAction(file_actions.save_as)
        toolbar.addAction(file_actions.load)
        toolbar.addAction(file_actions.autosave)
        toolbar.addSeparator()
        toolbar.addAction(run_actions.start)
        toolbar.addAction(run_actions.stop)
        toolbar.addSeparator()
        toolbar.addAction(file_actions.exit)
        self.addToolBar(toolbar)

    def init_statusbar(self) -> None:
        """Initialize the status bar."""
        statusbar = QStatusBar(self, sizeGripEnabled=True)
        init_widget(statusbar, "MandalaStatusBar")
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
            self, "Select Profile", str(self.profiles.profile_dir), "JSON Files (*.json)"
        )
        if filename:
            self.profiles.set_current(filename)
            self.profiles.open_profile(self)
            self.reset_window_title()

    @Slot()
    def reset_window_title(self) -> None:
        """Update the window title based on the current profile."""
        self.setWindowTitle(f"{Path(self.profiles.current_profile).stem} - Mandala: Copy random files")

    @Slot(str)
    def update_window_title(self, title: str) -> None:
        """Update the window title based on the current profile."""
        self.setWindowTitle(title)

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
