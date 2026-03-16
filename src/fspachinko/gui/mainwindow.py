"""Main module."""

from os.path import basename, splitext
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Slot
from PySide6.QtWidgets import QFileDialog, QMainWindow, QStatusBar, QToolBar

from ..adapters.profiles import ProfileManager
from ..constants import GUIFileDialogFilter, GUILabel, GUIName, GUISettingsKey, GUITitle
from .actions import Actions
from .centralwidget import CentralWidget

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__(animated=True)
        self.central_widget = CentralWidget()
        self.profiles = ProfileManager()
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
        self.central_widget.title_changed.connect(self.setWindowTitle)

    def init_menubar(self) -> None:
        """Initialize the menu bar."""
        menubar = self.menuBar()
        file_menu = menubar.addMenu(GUILabel.FILEMENU)
        file_menu.addAction(self._actions.file.save)
        file_menu.addAction(self._actions.file.save_as)
        file_menu.addAction(self._actions.file.load)
        file_menu.addSeparator()
        file_menu.addAction(self._actions.file.exit)
        run_menu = menubar.addMenu(GUILabel.RUNMENU)
        run_menu.addAction(self._actions.run.start)
        run_menu.addAction(self._actions.run.stop)

    def init_toolbar(self) -> None:
        """Initialize the toolbar."""
        toolbar = QToolBar(GUIName.TOOLBAR)
        toolbar.setObjectName(GUIName.TOOLBAR)
        toolbar.addAction(self._actions.file.save)
        toolbar.addAction(self._actions.file.save_as)
        toolbar.addAction(self._actions.file.load)
        toolbar.addSeparator()
        toolbar.addAction(self._actions.run.start)
        toolbar.addAction(self._actions.run.stop)
        toolbar.addSeparator()
        toolbar.addAction(self._actions.file.exit)
        self.addToolBar(toolbar)

    def init_statusbar(self) -> None:
        """Initialize the status bar."""
        statusbar = QStatusBar(self, sizeGripEnabled=True)
        self.setStatusBar(statusbar)

    def init_settings(self) -> None:
        """Initialize GUI settings manager."""
        qsettings = QSettings()
        if geometry := qsettings.value(GUISettingsKey.GEOMETRY):
            self.restoreGeometry(geometry)
        if state := qsettings.value(GUISettingsKey.STATE):
            self.restoreState(state)
        self.update_profile_path(str(qsettings.value(GUISettingsKey.PROFILE, "")))
        self.open_profile()

    @Slot()
    def save_profile(self) -> None:
        """Save the current profile."""
        self.profiles.set(self.central_widget.capture_config())

    def open_profile(self) -> None:
        """Open the current profile."""
        self.central_widget.restore_config(self.profiles.get())

    @Slot()
    def save_profile_as_dialog(self) -> None:
        """Save a GUI profile via dialog."""
        profile_path, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption=GUITitle.SAVE_PROFILE,
            dir=self.profiles.parent,
            filter=GUIFileDialogFilter.JSON,
        )
        if profile_path:
            self.update_profile_path(profile_path)
            self.save_profile()

    @Slot()
    def open_profile_dialog(self) -> None:
        """Load a GUI profile via dialog."""
        profile_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption=GUITitle.OPEN_PROFILE,
            dir=self.profiles.parent,
            filter=GUIFileDialogFilter.JSON,
        )
        if profile_path:
            self.update_profile_path(profile_path)
            self.open_profile()

    def update_profile_path(self, path: str) -> None:
        """Set the current profile path."""
        self.profiles.path = path
        self.setWindowTitle(get_window_title(self.profiles.path))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Handle window close event."""
        qsettings = QSettings()
        qsettings.setValue(GUISettingsKey.GEOMETRY, self.saveGeometry())
        qsettings.setValue(GUISettingsKey.STATE, self.saveState())
        qsettings.setValue(GUISettingsKey.PROFILE, self.profiles.path)
        super().closeEvent(event)


def get_window_title(path: str, title: str = GUITitle.WINDOW) -> str:
    """Generate a window title based on the profile path."""
    if path:
        profile_stem, _ = splitext(basename(path))
        return f"{profile_stem} - {title}"
    return title
