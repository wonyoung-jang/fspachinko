"""Main module."""

from enum import StrEnum
from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, QObject, QSettings, Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMenu, QToolBar

from fspachinko.adapters.loggers import AttachedLogHandler
from fspachinko.config import ConfigModel
from fspachinko.domain.commands import Command, ConfigurePipeline, RunTransferJob, SaveConfiguration, StopProcess
from fspachinko.domain.events import DirectoryStarted, FileTransferred, PipelineConfigured, RunFinished, RunStarted
from fspachinko.entrypoints.gui.components import BaseDockWidget, LogWidget, MainConfigWidget, ProgressWidget
from fspachinko.entrypoints.gui.helpers import (
    QtActionKey,
    get_qt_icon,
    get_qt_shortcut,
    menu_config,
    qt_action_config,
    toolbar_config,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PySide6.QtGui import QCloseEvent

    from fspachinko.bootstrap import Bootstrapper
    from fspachinko.service.messagebus import MessageBus


# -- Actions (View <> Presenter) ----------------------------------------------------------------
def build_actions(parent: QObject | None = None) -> dict[str, QAction]:
    """Build actions for the UI."""
    actions = {}
    for ac in qt_action_config():
        action = QAction(get_qt_icon(ac.iconfile), ac.text, parent)
        action.setShortcut(get_qt_shortcut(ac.shortcut))
        action.setToolTip(ac.tip)
        action.setStatusTip(ac.tip)
        actions[ac.name] = action
    return actions


# -- BusWorker (Model) ----------------------------------------------------------------
class BusWorker(QObject):
    """Worker for handling the message bus."""

    pipeline_configured = Signal(PipelineConfigured)
    run_started = Signal(RunStarted)
    directory_started = Signal(DirectoryStarted)
    file_transferred = Signal(FileTransferred)
    run_finished = Signal(RunFinished)

    def __init__(self, bus: MessageBus) -> None:
        """Initialize the worker with the message bus."""
        super().__init__()
        self._bus = bus
        self._bus.subscribe(PipelineConfigured, self.pipeline_configured.emit)
        self._bus.subscribe(RunStarted, self.run_started.emit)
        self._bus.subscribe(DirectoryStarted, self.directory_started.emit)
        self._bus.subscribe(FileTransferred, self.file_transferred.emit)
        self._bus.subscribe(RunFinished, self.run_finished.emit)

    @Slot(Command)
    def handle(self, cmd: Command) -> None:
        """Handle a command by passing it to the message bus."""
        self._bus.handle(cmd)


# -- MainWindow (View) -------------------------------------------------------------
class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, presenter: Presenter) -> None:
        """Initialize the main window."""
        super().__init__(animated=True)
        self._presenter = presenter
        self._ui = MainConfigWidget()
        self.setCentralWidget(self._ui)
        self._log_w = LogWidget(self)
        self._prog_w = ProgressWidget(self)
        area = Qt.DockWidgetArea.BottomDockWidgetArea
        logdock = BaseDockWidget("Log", "log-dock", self._log_w, self)
        progdock = BaseDockWidget("Progress", "progress-dock", self._prog_w, self)
        self.addDockWidget(area, logdock)
        self.addDockWidget(area, progdock)

    # -- IView -----------------------------------------------------------------

    @property
    def config(self) -> dict:
        return self._ui.config

    @property
    def file_prog_percentage(self) -> int:
        return self._prog_w.file_percentage

    def restore_config(self, config: dict) -> None:
        self._ui.restore(config)

    def toggle_ui(self, *, is_enabled: bool) -> None:
        self._ui.toggle(is_enabled=is_enabled)

    def append_log(self, text: str) -> None:
        self._log_w.append(text)

    def update_progress_start(self, count: int) -> None:
        self._prog_w.handle_start_process(count)

    def update_progress_directory(self, qty: int) -> None:
        self._prog_w.handle_directory_start(qty)

    def update_progress_file(self) -> None:
        self._prog_w.handle_file_transfer()

    def build_ui_bars(self, actions: dict[str, QAction]) -> None:
        def _populate(bar: QToolBar | QMenu, items: Sequence[str | None]) -> None:
            for item in items:
                if item is None:
                    bar.addSeparator()
                else:
                    bar.addAction(actions[item])

        self.statusBar().setSizeGripEnabled(True)
        toolbar = self.addToolBar("Toolbar")
        toolbar.setObjectName("Toolbar")
        _populate(toolbar, toolbar_config())
        for submenu, config in menu_config().items():
            _populate(self.menuBar().addMenu(submenu), config)

    # -- Lifecycle -------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._presenter.cleanup()
        super().closeEvent(event)


# -- Presenter (Presenter) ----------------------------------------------------------------
class Presenter(QObject):
    """Presenter for the main window."""

    _sig_cmd = Signal(Command)
    _sig_stop = Signal(StopProcess)
    _sig_logged = Signal(str)

    class GUIStateKey(StrEnum):
        """Enumeration for QSettings keys."""

        CONFIG = "config"
        GEOMETRY = "geometry"
        STATE = "state"

    class GUITitle(StrEnum):
        """Enumeration for GUI window titles."""

        OPEN_CONFIG = "Open Configuration"
        SAVE_CONFIG = "Save Configuration As"
        WINDOW = "fspachinko: Transfer random files"

    def __init__(self, bootstrapper: Bootstrapper) -> None:
        """Initialize the presenter with the bootstrapper."""
        super().__init__()
        self._bootstrapper = bootstrapper
        self._fs = bootstrapper.fs
        self._configs = bootstrapper.config_manager
        self._worker = BusWorker(bootstrapper.build_message_bus())
        self._thread = QThread(self)
        self._actions = build_actions(self)
        self._view = MainWindow(self)
        self._original_title = self._view.windowTitle()
        self._view.build_ui_bars(self._actions)
        self._connect_signals()
        self._restore_state()
        self._setup_worker()

    def _restore_state(self) -> None:
        """Restore the window state from settings."""
        qsettings = QSettings()
        if (geometry := qsettings.value(Presenter.GUIStateKey.GEOMETRY)) and isinstance(
            geometry, QByteArray | bytes | bytearray | memoryview
        ):
            self._view.restoreGeometry(geometry)
        if (state := qsettings.value(Presenter.GUIStateKey.STATE)) and isinstance(
            state, QByteArray | bytes | bytearray | memoryview
        ):
            self._view.restoreState(state)
        if (path := qsettings.value(Presenter.GUIStateKey.CONFIG)) and isinstance(path, str):
            self._load_config(path)

    def _setup_worker(self) -> None:
        """Set up the worker and its signals."""
        self._worker.moveToThread(self._thread)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _connect_signals(self) -> None:
        """Connect signals for the UI."""
        # Logger
        self._bootstrapper.logger.add_handler("qtgui", AttachedLogHandler(self._sig_logged.emit))
        self._sig_logged.connect(self._view.append_log)
        # Action -> Presenter -> Worker (Commands)
        self._actions[QtActionKey.START].triggered.connect(self.start)
        self._actions[QtActionKey.STOP].triggered.connect(self.stop)
        self._actions[QtActionKey.SAVE].triggered.connect(self.save)
        self._actions[QtActionKey.SAVE_AS].triggered.connect(self.save_as)
        self._actions[QtActionKey.LOAD].triggered.connect(self.open)
        self._actions[QtActionKey.EXIT].triggered.connect(self.close)
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
                root=cfg.root.path,
                max_per_dir=cfg.options.max_per_dir,
            )
        )

    @Slot()
    def stop(self) -> None:
        self._sig_stop.emit(StopProcess())

    @Slot()
    def save(self) -> None:
        self._sig_cmd.emit(
            SaveConfiguration(
                path=self._configs.current,
                config=self._view.config,
            )
        )

    @Slot()
    def save_as(self) -> None:
        if path := self._file_dialog(save=True):
            self._set_config_path(path)
            self._sig_cmd.emit(
                SaveConfiguration(
                    path=self._configs.current,
                    config=self._view.config,
                )
            )

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
        self._original_title = self._view.windowTitle()

    @Slot(DirectoryStarted)
    def _on_directory_started(self, evt: DirectoryStarted) -> None:
        self._view.update_progress_directory(evt.target_qty)

    @Slot(FileTransferred)
    def _on_file_transferred(self, _evt: FileTransferred) -> None:
        self._view.update_progress_file()
        self._view.setWindowTitle(f"[{self._view.file_prog_percentage}%] {self._original_title}")

    @Slot(RunFinished)
    def _on_run_finished(self, _evt: RunFinished) -> None:
        self._view.toggle_ui(is_enabled=True)
        self._view.setWindowTitle(self._original_title)

    # -- Helpers ---------------------------------------------------------------

    def _file_dialog(self, *, save: bool) -> str | None:
        fn = QFileDialog.getSaveFileName if save else QFileDialog.getOpenFileName
        path, _ = fn(
            parent=self._view,
            caption=Presenter.GUITitle.SAVE_CONFIG if save else Presenter.GUITitle.OPEN_CONFIG,
            dir=self._configs.directory,
            filter="JSON Files (*.json)",
        )
        return path or None

    def _set_config_path(self, path: str) -> None:
        self._configs.current = path
        stem = self._fs.get_stem_and_ext(path)[0] if path else "None"
        self._view.setWindowTitle(f"{stem} - {Presenter.GUITitle.WINDOW}")

    def _load_config(self, path: str) -> None:
        self._set_config_path(path)
        self._view.restore_config(self._fs.json_to_dict(path))

    # -- Lifecycle -------------------------------------------------------------

    def show(self) -> None:
        """Show the main window."""
        self._view.show()

    def close(self) -> None:
        """Close the main window."""
        self._view.close()

    def cleanup(self) -> None:
        """Stop worker and persist window state. Called from closeEvent."""
        self.stop()
        self._thread.quit()
        self._thread.wait()
        settings = QSettings()
        settings.setValue(Presenter.GUIStateKey.GEOMETRY, self._view.saveGeometry())
        settings.setValue(Presenter.GUIStateKey.STATE, self._view.saveState())
        settings.setValue(Presenter.GUIStateKey.CONFIG, self._configs.current)
