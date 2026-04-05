"""Main module."""

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, QSettings, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMenu, QToolBar, QVBoxLayout, QWidget

from fspachinko.config import ConfigModel
from fspachinko.datapaths import get_config_path
from fspachinko.domain.commands import RunTransferJob, SaveConfiguration, StopProcess
from fspachinko.domain.events import DirectoryStarted, FileTransferred
from fspachinko.entrypoints.gui.components import (
    Actions,
    BaseDockWidget,
    BaseGroupBox,
    LogWidget,
    ProgressWidget,
    get_component_map,
)
from fspachinko.entrypoints.gui.constants import (
    MENU_STRUCTURE,
    TOOLBAR_STRUCTURE,
    GUIFileDialogFilter,
    GUIName,
    GUISettingsKey,
    GUITitle,
)

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent

    from fspachinko.bootstrap import FSPachinkoBootstrapper


class MainConfigWidget(QWidget):
    """Main widget."""

    def __init__(self, *config_widgets: BaseGroupBox) -> None:
        """Initialize the main widget."""
        super().__init__()
        self._config_widgets: tuple[BaseGroupBox, ...] = tuple(config_widgets)
        layout = QVBoxLayout(self)
        for w in self._config_widgets:
            layout.addWidget(w)

    @property
    def config(self) -> dict:
        """Capture the current configuration from the UI."""
        config = {}
        for w in self._config_widgets:
            config.update(w.config)
        return config

    def restore_config(self, config: dict) -> None:
        """Restore the configuration to the UI."""
        for w in self._config_widgets:
            w.restore(config)

    def toggle(self, *, is_enabled: bool) -> None:
        """Lock or unlock UI elements."""
        for w in self._config_widgets:
            w.setEnabled(is_enabled)


def build_ui_bars(window: QMainWindow, actions: Actions) -> None:
    """Build the status, tool, and menu bars."""

    def add_actions_to_bar(
        bar: QToolBar | QMenu, actions: Actions, actions_names: list[str | None] | list[str]
    ) -> None:
        """Add actions to a menu or toolbar based on a list of action keys."""
        for item in actions_names:
            if item is None:
                bar.addSeparator()
            else:
                action = getattr(actions, item)
                bar.addAction(action)

    statusbar = window.statusBar()
    statusbar.setSizeGripEnabled(True)
    toolbar = window.addToolBar(GUIName.TOOLBAR)
    toolbar.setObjectName(GUIName.TOOLBAR)
    add_actions_to_bar(toolbar, actions, TOOLBAR_STRUCTURE)
    menubar = window.menuBar()
    for menu_name, action_keys in MENU_STRUCTURE.items():
        menu = menubar.addMenu(menu_name)
        add_actions_to_bar(menu, actions, action_keys)


class QtLogHandlerSignals(QObject):
    """Signals for the LogHandler."""

    logged = Signal(str)


class QtLogHandler(logging.Handler):
    """A logging handler that emits log messages to a Qt signal."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the handler and its signals."""
        super().__init__(*args, **kwargs)
        self.signals = QtLogHandlerSignals()
        self.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
        self.setLevel(logging.INFO)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by formatting it and emitting the text_written signal."""
        msg = self.format(record)
        self.signals.logged.emit(msg)


class BusWorker(QObject):
    """Worker for handling the message bus."""

    directory_started = Signal(DirectoryStarted)
    file_transferred = Signal(FileTransferred)
    started = Signal()
    finished = Signal()
    pipeline_configured = Signal(int)

    def __init__(self, bootstrapper: FSPachinkoBootstrapper) -> None:
        """Initialize the worker with the bootstrapper."""
        super().__init__()
        self.bootstrapper = bootstrapper
        self.bus = self.bootstrapper.build_message_bus()
        self.bus.subscribe(DirectoryStarted, self.directory_started.emit)
        self.bus.subscribe(FileTransferred, self.file_transferred.emit)

    @Slot(RunTransferJob)
    def run(self, cmd: RunTransferJob) -> None:
        """Run the transfer job."""
        self.started.emit()
        self.bus.handle(cmd)
        self.finished.emit()

    @Slot(StopProcess)
    def stop(self, cmd: StopProcess) -> None:
        """Stop the worker."""
        self.bus.handle(cmd)

    @Slot(SaveConfiguration)
    def save_config(self, cmd: SaveConfiguration) -> None:
        """Save the configuration."""
        self.bus.handle(cmd)

    @Slot(ConfigModel)
    def configure_pipeline(self, config: ConfigModel) -> None:
        """Configure the pipeline for a run."""
        self.bootstrapper.configure_pipeline_for_run(config)
        self.pipeline_configured.emit(config.directory.count)


class MainWindow(QMainWindow):
    """Main application window."""

    _configure_pipeline_requested = Signal(ConfigModel)
    _run_requested = Signal(RunTransferJob)
    _stop_requested = Signal(StopProcess)
    _save_config_requested = Signal(SaveConfiguration)

    def __init__(self, bootstrapper: FSPachinkoBootstrapper) -> None:
        """Initialize the main window."""
        super().__init__()
        self.filesystem = bootstrapper.filesystem
        self._original_title = self.windowTitle()
        self._config_path = ""
        self._actions = Actions.build()
        gui_log_handler = QtLogHandler()
        bootstrapper.logger.add_handler("qtgui", gui_log_handler)
        self.log_signal = gui_log_handler.signals
        self.setAnimated(True)
        self.ui = MainConfigWidget(*(w(title, name, *args) for w, title, name, *args in get_component_map()))
        self.setCentralWidget(self.ui)
        self.log_widget = LogWidget()
        self.progress_widget = ProgressWidget()
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, BaseDockWidget(self.log_widget, "LogDock"))
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, BaseDockWidget(self.progress_widget, "ProgressDock"))
        build_ui_bars(self, self._actions)
        self._thread = QThread()
        self._worker = BusWorker(bootstrapper)
        self._worker.moveToThread(self._thread)
        self._worker.started.connect(self.handle_run_started)
        self._worker.pipeline_configured.connect(self.handle_pipeline_configured)
        self._worker.directory_started.connect(self.handle_directory_started)
        self._worker.file_transferred.connect(self.handle_file_transferred)
        self._worker.finished.connect(self.handle_run_finished)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()
        qsettings = QSettings()
        if (geometry := qsettings.value(GUISettingsKey.GEOMETRY)) and isinstance(geometry, bytes | bytearray):
            self.restoreGeometry(geometry)
        if (state := qsettings.value(GUISettingsKey.STATE)) and isinstance(state, bytes | bytearray):
            self.restoreState(state)
        if config_path := qsettings.value(GUISettingsKey.CONFIG):
            self._config_path = get_config_path(config_path)
            self.setWindowTitle(self.get_window_title())
            self.ui.restore_config(self.filesystem.json_to_dict(self._config_path))
        self._configure_pipeline_requested.connect(self._worker.configure_pipeline)
        self._run_requested.connect(self._worker.run)
        self._stop_requested.connect(self._worker.stop, Qt.ConnectionType.DirectConnection)
        self._save_config_requested.connect(self._worker.save_config)
        self.log_signal.logged.connect(self.log_widget.append)
        self._actions.save.triggered.connect(self.save_config)
        self._actions.save_as.triggered.connect(self.save_config_as)
        self._actions.load.triggered.connect(self.open_config)
        self._actions.exit.triggered.connect(self.close)
        self._actions.start.triggered.connect(self.start)
        self._actions.stop.triggered.connect(self.stop)

    @Slot()
    def start(self) -> None:
        """Start the process and disable UI elements."""
        c = ConfigModel.model_validate(self.ui.config)
        self._configure_pipeline_requested.emit(c)
        self._run_requested.emit(
            RunTransferJob(
                root=c.root,
                max_per_dir=c.options.max_per_dir,
                unique_files_only=c.options.is_create_unique_dirs,
            )
        )

    @Slot()
    def stop(self) -> None:
        """Stop the process."""
        self._stop_requested.emit(StopProcess())

    @Slot()
    def save_config(self) -> None:
        """Save the current config."""
        self._save_config_requested.emit(SaveConfiguration(path=self._config_path, config=self.ui.config))

    @Slot()
    def save_config_as(self) -> None:
        """Save a GUI config via dialog."""
        config_path, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption=GUITitle.SAVE_CONFIG,
            dir=self.filesystem.get_parent(self._config_path),
            filter=GUIFileDialogFilter.JSON,
        )
        if config_path:
            self._config_path = get_config_path(config_path)
            self.setWindowTitle(self.get_window_title())
            self.save_config()

    @Slot()
    def open_config(self) -> None:
        """Load a GUI config via dialog."""
        config_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption=GUITitle.OPEN_CONFIG,
            dir=self.filesystem.get_parent(self._config_path),
            filter=GUIFileDialogFilter.JSON,
        )
        if config_path:
            self._config_path = get_config_path(config_path)
            self.setWindowTitle(self.get_window_title())
            self.ui.restore_config(self.filesystem.json_to_dict(self._config_path))

    @Slot(FileTransferred)
    def handle_file_transferred(self, evt: FileTransferred) -> None:
        """Update the window title with the current progress."""
        self.progress_widget.handle_file_transfer(evt.count)
        self.setWindowTitle(f"[{self.progress_widget.file_percentage}%] {self._original_title}")

    @Slot(DirectoryStarted)
    def handle_directory_started(self, cmd: DirectoryStarted) -> None:
        """Update the window title with the current progress."""
        self.progress_widget.handle_directory_start(cmd.target_qty)

    @Slot(int)
    def handle_pipeline_configured(self, count: int) -> None:
        """Initialize the progress widget with the total number of folders."""
        self.progress_widget.handle_start_process(count)

    @Slot()
    def handle_run_started(self) -> None:
        """Handle the start of a run."""
        self.ui.toggle(is_enabled=False)
        self._original_title = self.windowTitle()

    @Slot()
    def handle_run_finished(self) -> None:
        """Handle the end of a run."""
        self.ui.toggle(is_enabled=True)
        self.setWindowTitle(self._original_title)

    def get_window_title(self) -> str:
        """Generate a window title based on the config path."""
        if self._config_path:
            stem, _ = self.filesystem.get_stem_and_ext(self._config_path)
        else:
            stem = "None"
        return f"{stem} - {GUITitle.WINDOW}"

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Handle window close event."""
        self.stop()
        self._thread.quit()
        self._thread.wait()
        qsettings = QSettings()
        qsettings.setValue(GUISettingsKey.GEOMETRY, self.saveGeometry())
        qsettings.setValue(GUISettingsKey.STATE, self.saveState())
        qsettings.setValue(GUISettingsKey.CONFIG, self._config_path)
        super().closeEvent(event)
