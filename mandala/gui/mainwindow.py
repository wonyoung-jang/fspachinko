"""Main module for Mandala."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Slot
from PySide6.QtWidgets import QFileDialog, QMainWindow, QStatusBar, QToolBar

from .centralwidget import MandalaCentralGui
from .settings import ProfileManager

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent


@dataclass(slots=True)
class MandalaMainWindow(QMainWindow):
    """Main application window for Mandala."""

    ui: MandalaCentralGui = field(init=False)
    profiles: ProfileManager = field(init=False)
    qsettings: QSettings = field(default_factory=QSettings)

    def __post_init__(self) -> None:
        """Initialize the main window."""
        super().__init__()

        self.ui = MandalaCentralGui()
        self.setCentralWidget(self.ui)

        self.init_toolbar()
        self.init_menubar()
        self.init_statusbar()

        self.profiles = ProfileManager()
        self.init_settings()

        self.ui.ui_execution.signal_close.connect(self.close)

        self.setWindowTitle(f"{Path(self.profiles.current_profile).stem} - Mandala: Copy random files")

    def init_menubar(self) -> None:
        """Initialize the menu bar."""
        menubar = self.menuBar()
        menubar.setObjectName("MainMenuBar")
        filemenu = menubar.addMenu("File")

        save_config_action = filemenu.addAction("Save Profile")
        save_config_action.setShortcut("Ctrl+S")
        save_config_action.setStatusTip("Save the current GUI profile")
        save_config_action.triggered.connect(self.save_profile)

        save_config_as_action = filemenu.addAction("Save Profile As")
        save_config_as_action.setShortcut("Ctrl+Shift+S")
        save_config_as_action.setStatusTip("Save the current GUI profile as...")
        save_config_as_action.triggered.connect(self.save_profile_as_dialog)

        load_config_action = filemenu.addAction("Load Profile")
        load_config_action.setShortcut("Ctrl+O")
        load_config_action.setStatusTip("Load a GUI profile")
        load_config_action.triggered.connect(self.open_profile_dialog)

    def init_toolbar(self) -> None:
        """Initialize the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setObjectName("MainToolbar")
        self.addToolBar(toolbar)

    def init_statusbar(self) -> None:
        """Initialize the status bar."""
        statusbar = QStatusBar(self, sizeGripEnabled=True)
        statusbar.setObjectName("MainStatusBar")
        self.setStatusBar(statusbar)

    def init_settings(self) -> None:
        """Initialize GUI settings manager."""
        self.restoreGeometry(self.qsettings.value("geometry"))
        self.restoreState(self.qsettings.value("state"))
        self.profiles.set_current(str(self.qsettings.value("profile", "")))
        self.profiles.open_profile(self)

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
            self.setWindowTitle(f"{Path(filename).stem} - Mandala: Copy random files")

    @Slot()
    def open_profile_dialog(self) -> None:
        """Load a GUI profile via dialog."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Profile", str(self.profiles.profile_dir), "JSON Files (*.json)"
        )
        if filename:
            self.profiles.set_current(filename)
            self.profiles.open_profile(self)
            self.setWindowTitle(f"{Path(filename).stem} - Mandala: Copy random files")

    def save_settings(self) -> None:
        """Save GUI settings on close."""
        self.qsettings.setValue("geometry", self.saveGeometry())
        self.qsettings.setValue("state", self.saveState())
        self.qsettings.setValue("profile", self.profiles.current_profile)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Handle window close event."""
        self.save_settings()
        super().closeEvent(event)
