"""Main module."""

from os.path import basename, dirname, splitext
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Slot
from PySide6.QtWidgets import QFileDialog, QMainWindow

from fspachinko.adapters.filesystemport import get_available_transfer_modes, get_profile_path
from fspachinko.configuration.repository import JSONConfigRepository
from fspachinko.constants import ByteUnit, GUIFileDialogFilter, GUILabel, GUIName, GUISettingsKey, GUITitle, TimeUnit

from .actions import Actions
from .centralwidget import CentralWidget
from .components import LogWidget, ProgressWidget
from .loggers_gui import setup_gui_logger
from .workers import ProcessController

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.setAnimated(True)
        self._original_title = ""
        self.config_path = ""
        self.actions_ = Actions.build()
        self.config_repo = JSONConfigRepository()
        self.controller = ProcessController()
        self.log_signal = setup_gui_logger()
        self.logging = LogWidget()
        self.progress = ProgressWidget()
        self.ui = CentralWidget(
            size_units=tuple(ByteUnit),
            dur_units=tuple(TimeUnit),
            transfermodes=tuple(get_available_transfer_modes().keys()),
        )
        self.ui.add_to_layout(self.logging, self.progress)
        self.setCentralWidget(self.ui)
        self.init_connections()
        self.init_menubar()
        self.init_toolbar()
        self.init_statusbar()
        self.init_settings()

    @property
    def config_parent(self) -> str:
        """Get the parent directory of the current profile."""
        return dirname(self.config_path)

    def init_connections(self) -> None:
        """Initialize connections."""
        self.log_signal.logged.connect(self.logging.append)
        self.actions_.save.triggered.connect(self.save_profile)
        self.actions_.save_as.triggered.connect(self.save_profile_as_dialog)
        self.actions_.load.triggered.connect(self.open_profile_dialog)
        self.actions_.exit.triggered.connect(self.close)
        self.actions_.start.triggered.connect(self.on_start)
        self.actions_.stop.triggered.connect(self.on_stop)
        self.controller.signals.process_started.connect(self.handle_start_process)
        self.controller.signals.directory_started.connect(self.handle_directory_start)
        self.controller.signals.file_transferred.connect(self.handle_file_transfer)
        self.controller.signals.finished.connect(self.handle_finished)

    def init_menubar(self) -> None:
        """Initialize the menu bar."""
        menubar = self.menuBar()
        file_menu = menubar.addMenu(GUILabel.FILEMENU)
        file_menu.addAction(self.actions_.save)
        file_menu.addAction(self.actions_.save_as)
        file_menu.addAction(self.actions_.load)
        file_menu.addSeparator()
        file_menu.addAction(self.actions_.exit)
        run_menu = menubar.addMenu(GUILabel.RUNMENU)
        run_menu.addAction(self.actions_.start)
        run_menu.addAction(self.actions_.stop)

    def init_toolbar(self) -> None:
        """Initialize the toolbar."""
        toolbar = self.addToolBar(GUIName.TOOLBAR)
        toolbar.setObjectName(GUIName.TOOLBAR)
        toolbar.addAction(self.actions_.save)
        toolbar.addAction(self.actions_.save_as)
        toolbar.addAction(self.actions_.load)
        toolbar.addAction(self.actions_.start)
        toolbar.addAction(self.actions_.stop)
        toolbar.addAction(self.actions_.exit)

    def init_statusbar(self) -> None:
        """Initialize the status bar."""
        statusbar = self.statusBar()
        statusbar.setSizeGripEnabled(True)

    def init_settings(self) -> None:
        """Initialize GUI settings manager."""
        qsettings = QSettings()
        if (geometry := qsettings.value(GUISettingsKey.GEOMETRY)) and isinstance(geometry, bytes | bytearray):
            self.restoreGeometry(geometry)
        if (state := qsettings.value(GUISettingsKey.STATE)) and isinstance(state, bytes | bytearray):
            self.restoreState(state)
        if profile_path := str(qsettings.value(GUISettingsKey.PROFILE, "")):
            self.update_profile_path(profile_path)
            self.open_profile()

    @Slot()
    def save_profile(self) -> None:
        """Save the current profile."""
        self.config_repo.set(self.config_path, self.ui.config)

    def open_profile(self) -> None:
        """Open the current profile."""
        self.ui.restore_config(self.config_repo.get(self.config_path))

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
        self.config_path = get_profile_path(path)
        self.setWindowTitle(self.get_window_title())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Handle window close event."""
        qsettings = QSettings()
        qsettings.setValue(GUISettingsKey.GEOMETRY, self.saveGeometry())
        qsettings.setValue(GUISettingsKey.STATE, self.saveState())
        qsettings.setValue(GUISettingsKey.PROFILE, self.config_path)
        super().closeEvent(event)

    @Slot()
    def on_start(self) -> None:
        """Start the process and disable UI elements."""
        self._original_title = self.windowTitle()
        self.ui.toggle(is_enabled=False)
        self.controller.start(self.config_repo.model_from_dict(self.ui.config))

    @Slot()
    def on_stop(self) -> None:
        """Stop the process."""
        self.controller.stop()

    @Slot(int)
    def handle_start_process(self, dir_count: int) -> None:
        """Handle the start of the process."""
        self.progress.handle_start_process(dir_count)

    @Slot(int)
    def handle_directory_start(self, target: int) -> None:
        """Update the directory progress bar."""
        self.progress.handle_directory_start(target)

    @Slot()
    def handle_file_transfer(self) -> None:
        """Update the window title with the current progress."""
        self.progress.handle_file_transfer()
        self.setWindowTitle(f"[{self.progress.file_percentage}%] {self._original_title}")

    @Slot()
    def handle_finished(self) -> None:
        """Reset the window title to the original."""
        self.ui.toggle(is_enabled=True)
        self.setWindowTitle(self._original_title)

    def get_window_title(self) -> str:
        """Generate a window title based on the profile path."""
        if self.config_path:
            profile_stem, _ = splitext(basename(self.config_path))
            return f"{profile_stem} - {GUITitle.WINDOW}"
        return GUITitle.WINDOW
