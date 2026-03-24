"""Main module."""

from os.path import basename, dirname, splitext
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Slot
from PySide6.QtWidgets import QFileDialog, QMainWindow

from fspachinko.adapters.filesystemport import get_profile_path
from fspachinko.adapters.transfer import FileTransferFnManager
from fspachinko.bootstrap import setup_bus
from fspachinko.configuration.repository import JSONConfigRepository
from fspachinko.constants import SIZE_MAP, TIME_MAP
from fspachinko.domain.commands import RunTransferJob, SaveProfile, StopProcess
from fspachinko.domain.events import DirectoryStarted, FileTransferred

from .centralwidget import CentralWidget
from .components import Actions, LogWidget, ProgressWidget
from .constants_gui import GUIFileDialogFilter, GUISettingsKey, GUITitle
from .loggers_gui import setup_gui_logger
from .qthelpers import build_ui_bars
from .workers import ProcessController

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent

    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.service.messagebus import MessageBus


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, bus: MessageBus, pipeline: AbstractPipeline) -> None:
        """Initialize the main window."""
        super().__init__()
        self.bus: MessageBus = bus
        self.pipeline: AbstractPipeline = pipeline
        self._actions: Actions = Actions.build()
        self._original_title = ""
        self.config_path = ""
        self.config_repo = JSONConfigRepository()
        self.controller = ProcessController()
        self.log_signal = setup_gui_logger()
        self.logging = LogWidget()
        self.progress = ProgressWidget()
        self.ui = CentralWidget(
            tuple(SIZE_MAP.keys()),
            tuple(TIME_MAP.keys()),
            FileTransferFnManager().transfermodes,
            self.logging,
            self.progress,
        )
        self.setCentralWidget(self.ui)
        self.setAnimated(True)
        build_ui_bars(self, self._actions)
        self.init_ui_settings()
        self.init_ui_connections()

    def init_ui_connections(self) -> None:
        """Initialize connections."""
        self.bus.subscribe(FileTransferred, self.handle_file_transferred)
        self.bus.subscribe(DirectoryStarted, self.handle_directory_started)
        self.log_signal.logged.connect(self.logging.append)
        self._actions.save.triggered.connect(self.save_profile)
        self._actions.save_as.triggered.connect(self.save_profile_as_dialog)
        self._actions.load.triggered.connect(self.open_profile_dialog)
        self._actions.exit.triggered.connect(self.on_close)
        self._actions.start.triggered.connect(self.on_start)
        self._actions.stop.triggered.connect(self.on_stop)
        self.controller.signals.process_started.connect(self.handle_start_process)
        self.controller.signals.finished.connect(self.handle_finished)
        self.controller.signals.stopped.connect(self.handle_stopped)

    def init_ui_settings(self) -> None:
        """Initialize GUI settings manager."""
        qsettings = QSettings()
        if (geometry := qsettings.value(GUISettingsKey.GEOMETRY)) and isinstance(geometry, bytes | bytearray):
            self.restoreGeometry(geometry)
        if (state := qsettings.value(GUISettingsKey.STATE)) and isinstance(state, bytes | bytearray):
            self.restoreState(state)
        if profile_path := str(qsettings.value(GUISettingsKey.PROFILE, "")):
            self.update_profile_path(profile_path)
            self.ui.restore_config(self.config_repo.json_to_dict(self.config_path))

    @Slot()
    def handle_start_process(self) -> None:
        """Handle the start of the process."""
        self.progress.handle_start_process(len(self.pipeline.dest_dir_inputs))
        self.bus.handle(RunTransferJob(dest_dir_inputs=self.pipeline.dest_dir_inputs))

    @Slot()
    def handle_stopped(self) -> None:
        """Handle the process being stopped."""
        self.bus.handle(StopProcess())

    @Slot()
    def save_profile(self) -> None:
        """Save the current profile."""
        self.bus.handle(SaveProfile(path=self.config_path, config=self.ui.config()))

    @Slot()
    def save_profile_as_dialog(self) -> None:
        """Save a GUI profile via dialog."""
        profile_path, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption=GUITitle.SAVE_PROFILE,
            dir=dirname(self.config_path),
            filter=GUIFileDialogFilter.JSON,
        )
        if profile_path:
            self.update_profile_path(profile_path)
            self.bus.handle(SaveProfile(path=self.config_path, config=self.ui.config()))

    @Slot()
    def open_profile_dialog(self) -> None:
        """Load a GUI profile via dialog."""
        profile_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption=GUITitle.OPEN_PROFILE,
            dir=dirname(self.config_path),
            filter=GUIFileDialogFilter.JSON,
        )
        if profile_path:
            self.update_profile_path(profile_path)
            self.ui.restore_config(self.config_repo.json_to_dict(self.config_path))

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
    def on_close(self) -> None:
        """Handle the close action."""
        self.on_stop()
        self.close()

    @Slot()
    def on_start(self) -> None:
        """Start the process and disable UI elements."""
        self._original_title = self.windowTitle()
        self.ui.toggle(is_enabled=False)
        config = self.config_repo.from_dict(self.ui.config())
        setup_bus(self.bus, config)
        self.controller.start()

    @Slot()
    def on_stop(self) -> None:
        """Stop the process."""
        self.controller.stop()

    def handle_file_transferred(self, _evt: FileTransferred) -> None:
        """Update the window title with the current progress."""
        self.progress.handle_file_transfer()
        self.setWindowTitle(f"[{self.progress.file_percentage}%] {self._original_title}")

    def handle_directory_started(self, cmd: DirectoryStarted) -> None:
        """Update the window title with the current progress."""
        self.progress.handle_directory_start(cmd.target_qty)

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
