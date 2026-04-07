"""Main module."""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from PySide6.QtCore import QByteArray, QObject, QSettings, Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMenu, QToolBar, QVBoxLayout, QWidget

from fspachinko.config import ConfigModel
from fspachinko.datapaths import get_config_path
from fspachinko.domain.commands import Command, ConfigurePipeline, RunTransferJob, SaveConfiguration, StopProcess
from fspachinko.domain.events import DirectoryStarted, FileTransferred, PipelineConfigured, RunFinished, RunStarted
from fspachinko.entrypoints.gui.components import BaseDockWidget, BaseGroupBox, LogWidget, ProgressWidget, component_map
from fspachinko.entrypoints.gui.constants import (
    ACTION_CONFIG,
    FILE_DIALOG_JSON_FILTER,
    MENU_CONFIG,
    TOOLBAR_CONFIG,
    TOOLBAR_NAME,
    GUIStateKey,
    GUITitle,
)
from fspachinko.entrypoints.gui.helpers import get_qt_icon, get_qt_shortcut, set_qt_tips

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PySide6.QtGui import QCloseEvent

    from fspachinko.bootstrap import FSPachinkoBootstrapper


# -- Actions ----------------------------------------------------------------
@dataclass(slots=True)
class Actions:
    """Main file menu actions."""

    save: QAction
    save_as: QAction
    load: QAction
    exit: QAction
    start: QAction
    stop: QAction

    @classmethod
    def build(cls, config: dict = ACTION_CONFIG) -> Actions:
        """Get file menu actions."""
        actions = {}
        for name, (text, tip) in config.items():
            actions[name] = QAction(get_qt_icon(name), text, shortcut=get_qt_shortcut(name))
            set_qt_tips(actions[name], tip)
        return cls(**actions)


# -- Log handler for GUI ----------------------------------------------------------------
class QtLogSignals(QObject):
    """Signals for the LogHandler."""

    logged = Signal(str)


class QtLogHandler(logging.Handler):
    """A logging handler that emits log messages to a Qt signal."""

    def __init__(self) -> None:
        """Initialize the handler and its signals."""
        super().__init__()
        self.signals = QtLogSignals()
        self.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
        self.setLevel(logging.INFO)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by formatting it and emitting the text_written signal."""
        self.signals.logged.emit(self.format(record))


# -- Worker ----------------------------------------------------------------
class BusWorker(QObject):
    """Worker for handling the message bus."""

    pipeline_configured = Signal(PipelineConfigured)
    run_started = Signal(RunStarted)
    directory_started = Signal(DirectoryStarted)
    file_transferred = Signal(FileTransferred)
    run_finished = Signal(RunFinished)

    def __init__(self, bootstrapper: FSPachinkoBootstrapper) -> None:
        """Initialize the worker with the bootstrapper."""
        super().__init__()
        self.bootstrapper = bootstrapper
        self.bus = self.bootstrapper.build_message_bus()
        self.bus.subscribe(PipelineConfigured, self.pipeline_configured.emit)
        self.bus.subscribe(RunStarted, self.run_started.emit)
        self.bus.subscribe(DirectoryStarted, self.directory_started.emit)
        self.bus.subscribe(FileTransferred, self.file_transferred.emit)
        self.bus.subscribe(RunFinished, self.run_finished.emit)

    @Slot(Command)
    def handle(self, cmd: Command) -> None:
        """Handle a command by passing it to the message bus."""
        self.bus.handle(cmd)


# -- Presenter ----------------------------------------------------------------
class Presenter(QObject):
    """Presenter for the main window."""

    _sig_cmd = Signal(Command)
    _sig_stop = Signal(StopProcess)

    def __init__(self, view: IView, bootstrapper: FSPachinkoBootstrapper) -> None:
        """Initialize the presenter with the bootstrapper."""
        super().__init__()
        self._view = view
        self._bootstrapper = bootstrapper
        self._fs = bootstrapper.filesystem
        self._original_title = view.get_window_title()
        self._config_path = ""
        self._log_handler = QtLogHandler()
        self._thread = QThread()
        self._worker = BusWorker(bootstrapper)
        self._actions = Actions.build()
        self._view.build_ui_bars(self._actions)
        self._restore_state()
        self._setup_worker()
        self._connect_signals()

    def _restore_state(self) -> None:
        """Restore the window state from settings."""
        qsettings = QSettings()
        if geometry := qsettings.value(GUIStateKey.GEOMETRY):
            self._view.restore_geometry(geometry) if isinstance(geometry, bytes | bytearray) else None
        if state := qsettings.value(GUIStateKey.STATE):
            self._view.restore_window_state(state) if isinstance(state, bytes | bytearray) else None
        if path := qsettings.value(GUIStateKey.CONFIG):
            self._load_config(path)

    def _setup_worker(self) -> None:
        """Set up the worker and its signals."""
        self._worker.moveToThread(self._thread)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _connect_signals(self) -> None:
        """Connect signals for the UI."""
        # Logger
        self._bootstrapper.logger.add_handler("qtgui", self._log_handler)
        self._log_handler.signals.logged.connect(self._view.append_log)
        # Action -> Presenter -> Worker (Commands)
        self._actions.start.triggered.connect(self.start)
        self._actions.stop.triggered.connect(self.stop)
        self._actions.save.triggered.connect(self.save)
        self._actions.save_as.triggered.connect(self.save_as)
        self._actions.load.triggered.connect(self.open)
        self._actions.exit.triggered.connect(self._view.close)
        # Presenter -> Worker (Commands)
        self._sig_cmd.connect(self._worker.handle, Qt.ConnectionType.QueuedConnection)
        self._sig_stop.connect(self._worker.handle, Qt.ConnectionType.DirectConnection)
        # Worker -> Presenter (Events)
        self._worker.pipeline_configured.connect(self._on_pipeline_configured)
        self._worker.run_started.connect(self._on_run_started)
        self._worker.directory_started.connect(self._on_directory_started)
        self._worker.file_transferred.connect(self._on_file_transferred)
        self._worker.run_finished.connect(self._on_run_finished)

    # -- Action slots ----------------------------------------------------------

    @Slot()
    def start(self) -> None:
        cfg = ConfigModel.model_validate(self._view.config)
        self._sig_cmd.emit(ConfigurePipeline(cfg))
        self._sig_cmd.emit(
            RunTransferJob(
                root=cfg.root,
                max_per_dir=cfg.options.max_per_dir,
                unique_files_only=cfg.options.is_create_unique_dirs,
            )
        )

    @Slot()
    def stop(self) -> None:
        self._sig_stop.emit(StopProcess())

    @Slot()
    def save(self) -> None:
        self._sig_cmd.emit(SaveConfiguration(path=self._config_path, config=self._view.config))

    @Slot()
    def save_as(self) -> None:
        if path := self._file_dialog(save=True):
            self._set_config_path(path)
            self._sig_cmd.emit(SaveConfiguration(path=self._config_path, config=self._view.config))

    @Slot()
    def open(self) -> None:
        if path := self._file_dialog(save=False):
            self._load_config(path)

    # -- Worker event slots ----------------------------------------------------

    @Slot(PipelineConfigured)
    def _on_pipeline_configured(self, evt: PipelineConfigured) -> None:
        self._view.update_progress_start(evt.dir_count)

    @Slot(RunStarted)
    def _on_run_started(self, _evt: RunStarted) -> None:
        self._view.toggle_ui(is_enabled=False)
        self._original_title = self._view.get_window_title()

    @Slot(DirectoryStarted)
    def _on_directory_started(self, evt: DirectoryStarted) -> None:
        self._view.update_progress_directory(evt.target_qty)

    @Slot(FileTransferred)
    def _on_file_transferred(self, evt: FileTransferred) -> None:
        self._view.update_progress_file(evt.count)
        self._view.set_window_title(f"[{self._view.get_progress_percentage()}%] {self._original_title}")

    @Slot(RunFinished)
    def _on_run_finished(self, _evt: RunFinished) -> None:
        self._view.toggle_ui(is_enabled=True)
        self._view.set_window_title(self._original_title)

    # -- Helpers ---------------------------------------------------------------

    def _file_dialog(self, *, save: bool) -> str | None:
        fn = QFileDialog.getSaveFileName if save else QFileDialog.getOpenFileName
        path, _ = fn(
            caption=GUITitle.SAVE_CONFIG if save else GUITitle.OPEN_CONFIG,
            dir=self._fs.get_parent(self._config_path),
            filter=FILE_DIALOG_JSON_FILTER,
        )
        return path or None

    def _set_config_path(self, path: str) -> None:
        self._config_path = get_config_path(path)
        stem = self._fs.get_stem_and_ext(path)[0] if path else "None"
        self._view.set_window_title(f"{stem} - {GUITitle.WINDOW}")

    def _load_config(self, path: str) -> None:
        self._set_config_path(path)
        self._view.restore_config(self._fs.json_to_dict(path))

    # -- Lifecycle -------------------------------------------------------------

    def cleanup(self) -> None:
        """Stop worker and persist window state. Called from closeEvent."""
        self.stop()
        self._thread.quit()
        self._thread.wait()
        settings = QSettings()
        settings.setValue(GUIStateKey.GEOMETRY, self._view.save_geometry())
        settings.setValue(GUIStateKey.STATE, self._view.save_window_state())
        settings.setValue(GUIStateKey.CONFIG, self._config_path)


# -- View UI/Widgets ----------------------------------------------------------------
class MainConfigWidget(QWidget):
    """Main widget."""

    def __init__(self, *widgets: BaseGroupBox) -> None:
        """Initialize the main widget."""
        super().__init__()
        self._widgets = tuple(widgets)
        layout = QVBoxLayout(self)
        for w in self._widgets:
            layout.addWidget(w)

    @property
    def config(self) -> dict:
        """Capture the current configuration from the UI."""
        return {k: v for w in self._widgets for k, v in w.config.items()}

    def restore_config(self, config: dict) -> None:
        """Restore the configuration to the UI."""
        for w in self._widgets:
            w.restore(config)

    def toggle(self, *, is_enabled: bool) -> None:
        for w in self._widgets:
            w.setEnabled(is_enabled)


# -- View Protocol ----------------------------------------------------------------
class IView(Protocol):
    """Interface the Presenter uses to drive the View."""

    @property
    def config(self) -> dict: ...
    def restore_config(self, config: dict) -> None: ...
    def toggle_ui(self, *, is_enabled: bool) -> None: ...
    def set_window_title(self, title: str) -> None: ...
    def append_log(self, text: str) -> None: ...
    def update_progress_start(self, count: int) -> None: ...
    def update_progress_directory(self, qty: int) -> None: ...
    def update_progress_file(self, count: int) -> None: ...
    def get_progress_percentage(self) -> int: ...
    def restore_geometry(self, data: bytes) -> bool: ...
    def restore_window_state(self, data: bytes) -> bool: ...
    def save_geometry(self) -> QByteArray: ...
    def save_window_state(self) -> QByteArray: ...
    def close(self) -> bool: ...
    def get_window_title(self) -> str: ...
    def build_ui_bars(self, actions: Actions) -> None: ...


# -- View MainWindow -------------------------------------------------------------
class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, bootstrapper: FSPachinkoBootstrapper) -> None:
        """Initialize the main window."""
        super().__init__()
        self.setAnimated(True)
        self._ui = MainConfigWidget(*(w(title, name, *args) for w, title, name, *args in component_map()))
        self._log_w = LogWidget()
        self._prog_w = ProgressWidget()
        self.setCentralWidget(self._ui)
        area = Qt.DockWidgetArea.BottomDockWidgetArea
        self.addDockWidget(area, BaseDockWidget(self._log_w, "Log", "log-dock"))
        self.addDockWidget(area, BaseDockWidget(self._prog_w, "Progress", "progress-dock"))
        self._presenter = Presenter(self, bootstrapper)

    # -- IView -----------------------------------------------------------------

    @property
    def config(self) -> dict:
        return self._ui.config

    def restore_config(self, config: dict) -> None:
        self._ui.restore_config(config)

    def toggle_ui(self, *, is_enabled: bool) -> None:
        self._ui.toggle(is_enabled=is_enabled)

    def set_window_title(self, title: str) -> None:
        self.setWindowTitle(title)

    def append_log(self, text: str) -> None:
        self._log_w.append(text)

    def update_progress_start(self, count: int) -> None:
        self._prog_w.handle_start_process(count)

    def update_progress_directory(self, qty: int) -> None:
        self._prog_w.handle_directory_start(qty)

    def update_progress_file(self, count: int) -> None:
        self._prog_w.handle_file_transfer(count)

    def get_progress_percentage(self) -> int:
        return self._prog_w.file_percentage

    def restore_geometry(self, data: bytes) -> bool:
        return self.restoreGeometry(data)

    def restore_window_state(self, data: bytes) -> bool:
        return self.restoreState(data)

    def save_geometry(self) -> QByteArray:
        return self.saveGeometry()

    def save_window_state(self) -> QByteArray:
        return self.saveState()

    def get_window_title(self) -> str:
        return self.windowTitle()

    def build_ui_bars(self, actions: Actions) -> None:
        def _populate_bar(bar: QToolBar | QMenu, items: Sequence[str | None]) -> None:
            for item in items:
                bar.addSeparator() if item is None else bar.addAction(getattr(actions, item))

        self.statusBar().setSizeGripEnabled(True)
        toolbar = self.addToolBar(TOOLBAR_NAME)
        toolbar.setObjectName(TOOLBAR_NAME)
        _populate_bar(toolbar, TOOLBAR_CONFIG)
        for name, keys in MENU_CONFIG.items():
            _populate_bar(self.menuBar().addMenu(name), keys)

    # -- Lifecycle -------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._presenter.cleanup()
        super().closeEvent(event)
