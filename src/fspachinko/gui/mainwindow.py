"""Main module."""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Slot
from PySide6.QtWidgets import QFileDialog, QMainWindow, QStatusBar, QToolBar

from ..utils import GUIFileDialogFilter, GUILabel, GUIName, GUISettingsKey, GUITitle, get_stem_and_ext
from .actions import Actions
from .centralwidget import CentralWidget
from .qthelpers import set_qt_name
from .settings import ProfileManager

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        logger.debug("Initializing GUI")
        self.central_widget = CentralWidget()
        self.profiles = ProfileManager()
        self.qsettings = QSettings()
        self._actions = Actions()
        self.setCentralWidget(self.central_widget)
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

        self._actions.run.start.triggered.connect(self.central_widget.on_start)
        self._actions.run.stop.triggered.connect(self.central_widget.on_stop)

    def init_menubar(self) -> None:
        """Initialize the menu bar."""
        menubar = self.menuBar()
        set_qt_name(menubar, GUIName.MENUBAR)

        file_menu = menubar.addMenu(GUILabel.FILEMENU)
        set_qt_name(file_menu, GUIName.FILEMENU)

        file_menu.addAction(self._actions.file.save)
        file_menu.addAction(self._actions.file.save_as)
        file_menu.addAction(self._actions.file.load)
        file_menu.addSeparator()
        file_menu.addAction(self._actions.file.autosave)
        file_menu.addSeparator()
        file_menu.addAction(self._actions.file.exit)

        run_menu = menubar.addMenu(GUILabel.RUNMENU)
        set_qt_name(run_menu, GUIName.RUNMENU)

        run_menu.addAction(self._actions.run.start)
        run_menu.addAction(self._actions.run.stop)

    def init_toolbar(self) -> None:
        """Initialize the toolbar."""
        toolbar = QToolBar(GUIName.TOOLBAR)
        set_qt_name(toolbar, GUIName.TOOLBAR)

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
        set_qt_name(statusbar, GUIName.STATUSBAR)

        self.setStatusBar(statusbar)

    def init_settings(self) -> None:
        """Initialize GUI settings manager."""
        self.restoreGeometry(self.qsettings.value(GUISettingsKey.GEOMETRY))
        self.restoreState(self.qsettings.value(GUISettingsKey.STATE))
        self.profiles.set_current(str(self.qsettings.value(GUISettingsKey.PROFILE, "")))
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
            parent=self,
            caption=GUITitle.SAVE_PROFILE,
            dir=self.profiles.get_current_profile_parent(),
            filter=GUIFileDialogFilter.JSON,
        )
        if filename:
            self.profiles.set_current(filename)
            self.save_profile()
            self.reset_window_title()

    @Slot()
    def open_profile_dialog(self) -> None:
        """Load a GUI profile via dialog."""
        filename, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption=GUITitle.OPEN_PROFILE,
            dir=self.profiles.get_current_profile_parent(),
            filter=GUIFileDialogFilter.JSON,
        )
        if filename:
            self.profiles.set_current(filename)
            self.profiles.open_profile(self)
            self.reset_window_title()

    @Slot()
    def reset_window_title(self) -> None:
        """Update the window title based on the current profile."""
        profile_stem, _ = get_stem_and_ext(self.profiles.current_profile)
        self.setWindowTitle(f"{profile_stem} - {GUITitle.WINDOW}")

    def save_settings(self) -> None:
        """Save GUI settings on close."""
        self.qsettings.setValue(GUISettingsKey.GEOMETRY, self.saveGeometry())
        self.qsettings.setValue(GUISettingsKey.STATE, self.saveState())
        self.qsettings.setValue(GUISettingsKey.PROFILE, self.profiles.current_profile)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Handle window close event."""
        self.save_settings()
        if self._actions.file.autosave.isChecked():
            self.save_profile()
        super().closeEvent(event)
