"""Main module."""

from os.path import basename, dirname, splitext
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Qt, Slot
from PySide6.QtWidgets import QDockWidget, QFileDialog, QMainWindow

from fspachinko.configuration.repository import JSONConfigRepository
from fspachinko.datapaths import get_config_path
from fspachinko.domain.commands import CreateTransferJob, RunTransferJob, SaveConfiguration, StopProcess
from fspachinko.domain.events import DirectoryStarted, FileTransferred
from fspachinko.entrypoints.gui.centralwidget import CentralWidget
from fspachinko.entrypoints.gui.components import COMPONENT_MAP, Actions, LogWidget, ProgressWidget
from fspachinko.entrypoints.gui.constants_gui import GUIFileDialogFilter, GUISettingsKey, GUITitle
from fspachinko.entrypoints.gui.loggers_gui import QtLogHandler
from fspachinko.entrypoints.gui.qthelpers import build_ui_bars
from fspachinko.entrypoints.gui.workers import ProcessController

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent

    from fspachinko.bootstrap import FSPachinkoBootstrapper
    from fspachinko.service.messagebus import MessageBus


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, bootstrapper: FSPachinkoBootstrapper) -> None:
        """Initialize the main window."""
        super().__init__()
        self.bootstrapper: FSPachinkoBootstrapper = bootstrapper
        self.bus: MessageBus = bootstrapper.bootstrap()
        self._actions: Actions = Actions.build()
        self._original_title = ""
        self.config_path = ""
        self.config_repo = JSONConfigRepository()
        self.controller = ProcessController()
        gui_log_handler = QtLogHandler()
        self.bus.logger.add_handler("qtgui", gui_log_handler)
        self.log_signal = gui_log_handler.signals
        self.log_widget = LogWidget()
        self.progress_widget = ProgressWidget()
        config_widgets = tuple(w(title, name, *args) for w, title, name, *args in COMPONENT_MAP)
        self.ui = CentralWidget(config_widgets)
        self.log_dock = QDockWidget()
        self.progress_dock = QDockWidget()
        self.log_dock.setWidget(self.log_widget)
        self.log_dock.setObjectName("LogDock")
        self.progress_dock.setWidget(self.progress_widget)
        self.progress_dock.setObjectName("ProgressDock")
        self.setAnimated(True)
        self.setCentralWidget(self.ui)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.progress_dock)
        build_ui_bars(self, self._actions)
        self.init_ui_settings()
        self.init_ui_connections()

    def init_ui_connections(self) -> None:
        """Initialize connections."""
        self.bus.subscribe(FileTransferred, self.handle_file_transferred)
        self.bus.subscribe(DirectoryStarted, self.handle_directory_started)
        self.log_signal.logged.connect(self.log_widget.append)
        self._actions.save.triggered.connect(self.save_config)
        self._actions.save_as.triggered.connect(self.save_config_as_dialog)
        self._actions.load.triggered.connect(self.open_config_dialog)
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
        if profile_path := str(qsettings.value(GUISettingsKey.CONFIG, "")):
            self.update_config_path(profile_path)
            self.ui.restore_config(self.config_repo.json_to_dict(self.config_path))

    @Slot()
    def handle_start_process(self) -> None:
        """Handle the start of the process."""
        self.bus.handle(RunTransferJob())

    @Slot()
    def handle_stopped(self) -> None:
        """Handle the process being stopped."""
        self.bus.handle(StopProcess())

    @Slot()
    def save_config(self) -> None:
        """Save the current config."""
        self.bus.handle(SaveConfiguration(path=self.config_path, config=self.ui.config))

    @Slot()
    def save_config_as_dialog(self) -> None:
        """Save a GUI config via dialog."""
        config_path, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption=GUITitle.SAVE_CONFIG,
            dir=dirname(self.config_path),
            filter=GUIFileDialogFilter.JSON,
        )
        if config_path:
            self.update_config_path(config_path)
            self.bus.handle(SaveConfiguration(path=self.config_path, config=self.ui.config))

    @Slot()
    def open_config_dialog(self) -> None:
        """Load a GUI config via dialog."""
        config_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption=GUITitle.OPEN_CONFIG,
            dir=dirname(self.config_path),
            filter=GUIFileDialogFilter.JSON,
        )
        if config_path:
            self.update_config_path(config_path)
            self.ui.restore_config(self.config_repo.json_to_dict(self.config_path))

    def update_config_path(self, path: str) -> None:
        """Set the current config path."""
        self.config_path = get_config_path(path)
        self.setWindowTitle(self.get_window_title())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Handle window close event."""
        qsettings = QSettings()
        qsettings.setValue(GUISettingsKey.GEOMETRY, self.saveGeometry())
        qsettings.setValue(GUISettingsKey.STATE, self.saveState())
        qsettings.setValue(GUISettingsKey.CONFIG, self.config_path)
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
        config = self.config_repo.from_dict(self.ui.config)
        self.bootstrapper.configure_pipeline_for_run(config)
        self.progress_widget.handle_start_process(config.directory.count)
        self.controller.on_start(
            self.bus,
            CreateTransferJob(
                root=config.root,
                max_per_dir=config.options.max_per_dir,
                unique_files_only=config.options.is_create_unique_dirs,
            ),
        )

    @Slot()
    def on_stop(self) -> None:
        """Stop the process."""
        self.controller.on_stop()

    def handle_file_transferred(self, _evt: FileTransferred) -> None:
        """Update the window title with the current progress."""
        self.progress_widget.handle_file_transfer()
        self.setWindowTitle(f"[{self.progress_widget.file_percentage}%] {self._original_title}")

    def handle_directory_started(self, cmd: DirectoryStarted) -> None:
        """Update the window title with the current progress."""
        self.progress_widget.handle_directory_start(cmd.target_qty)

    @Slot()
    def handle_finished(self) -> None:
        """Reset the window title to the original."""
        self.ui.toggle(is_enabled=True)
        self.setWindowTitle(self._original_title)

    def get_window_title(self) -> str:
        """Generate a window title based on the config path."""
        if self.config_path:
            config_stem, _ = splitext(basename(self.config_path))
            return f"{config_stem} - {GUITitle.WINDOW}"
        return GUITitle.WINDOW
