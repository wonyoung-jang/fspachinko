"""Main module."""

from os.path import basename, dirname, splitext
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Slot
from PySide6.QtWidgets import QFileDialog, QMainWindow, QStatusBar, QToolBar

from fspachinko.adapters.filesystemport import get_profile_path
from fspachinko.configuration.repository import JSONConfigRepository
from fspachinko.constants import GUIFileDialogFilter, GUILabel, GUIName, GUISettingsKey, GUITitle

from .actions import get_actions
from .centralwidget import CentralWidget

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.central_widget = CentralWidget()
        self.config_repo = JSONConfigRepository()
        self.acts = get_actions()
        self._path = ""
        self.setAnimated(True)
        self.setCentralWidget(self.central_widget)

        self.init_connections()
        self.init_menubar()
        self.init_toolbar()
        self.init_statusbar()
        self.init_settings()

    @property
    def config_path(self) -> str:
        """Get the current profile path."""
        return self._path

    @config_path.setter
    def config_path(self, value: str) -> None:
        """Set the current profile path."""
        self._path = get_profile_path(value)

    @property
    def config_parent(self) -> str:
        """Get the parent directory of the current profile."""
        return dirname(self.config_path)

    def init_connections(self) -> None:
        """Initialize connections."""
        self.acts.save.triggered.connect(self.save_profile)
        self.acts.save_as.triggered.connect(self.save_profile_as_dialog)
        self.acts.load.triggered.connect(self.open_profile_dialog)
        self.acts.exit.triggered.connect(self.close)
        self.acts.start.triggered.connect(self.central_widget.on_start)
        self.acts.stop.triggered.connect(self.central_widget.on_stop)
        self.central_widget.title_changed.connect(self.setWindowTitle)

    def init_menubar(self) -> None:
        """Initialize the menu bar."""
        menubar = self.menuBar()
        file_menu = menubar.addMenu(GUILabel.FILEMENU)
        file_menu.addAction(self.acts.save)
        file_menu.addAction(self.acts.save_as)
        file_menu.addAction(self.acts.load)
        file_menu.addSeparator()
        file_menu.addAction(self.acts.exit)
        run_menu = menubar.addMenu(GUILabel.RUNMENU)
        run_menu.addAction(self.acts.start)
        run_menu.addAction(self.acts.stop)

    def init_toolbar(self) -> None:
        """Initialize the toolbar."""
        toolbar = QToolBar(GUIName.TOOLBAR)
        toolbar.setObjectName(GUIName.TOOLBAR)
        toolbar.addAction(self.acts.save)
        toolbar.addAction(self.acts.save_as)
        toolbar.addAction(self.acts.load)
        toolbar.addSeparator()
        toolbar.addAction(self.acts.start)
        toolbar.addAction(self.acts.stop)
        toolbar.addSeparator()
        toolbar.addAction(self.acts.exit)
        self.addToolBar(toolbar)

    def init_statusbar(self) -> None:
        """Initialize the status bar."""
        statusbar = QStatusBar()
        statusbar.setSizeGripEnabled(True)
        self.setStatusBar(statusbar)

    def init_settings(self) -> None:
        """Initialize GUI settings manager."""
        qsettings = QSettings()
        if (geometry := qsettings.value(GUISettingsKey.GEOMETRY)) and isinstance(geometry, bytes | bytearray):
            self.restoreGeometry(geometry)
        if (state := qsettings.value(GUISettingsKey.STATE)) and isinstance(state, bytes | bytearray):
            self.restoreState(state)
        self.update_profile_path(str(qsettings.value(GUISettingsKey.PROFILE, "")))
        self.open_profile()

    @Slot()
    def save_profile(self) -> None:
        """Save the current profile."""
        self.config_repo.set(self.config_path, self.central_widget.config)

    def open_profile(self) -> None:
        """Open the current profile."""
        self.central_widget.restore_config(self.config_repo.get(self.config_path))

    @Slot()
    def save_profile_as_dialog(self) -> None:
        """Save a GUI profile via dialog."""
        profile_path, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption=GUITitle.SAVE_PROFILE,
            dir=self.config_parent,
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
            dir=self.config_parent,
            filter=GUIFileDialogFilter.JSON,
        )
        if profile_path:
            self.update_profile_path(profile_path)
            self.open_profile()

    def update_profile_path(self, path: str) -> None:
        """Set the current profile path."""
        self.config_path = path
        self.setWindowTitle(get_window_title(self.config_path))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Handle window close event."""
        qsettings = QSettings()
        qsettings.setValue(GUISettingsKey.GEOMETRY, self.saveGeometry())
        qsettings.setValue(GUISettingsKey.STATE, self.saveState())
        qsettings.setValue(GUISettingsKey.PROFILE, self.config_path)
        super().closeEvent(event)


def get_window_title(path: str, title: str = GUITitle.WINDOW) -> str:
    """Generate a window title based on the profile path."""
    if path:
        profile_stem, _ = splitext(basename(path))
        return f"{profile_stem} - {title}"
    return title
