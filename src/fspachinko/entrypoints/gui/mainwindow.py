"""Main module."""

import logging
from os.path import basename, dirname, splitext
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, QSettings, Qt, Signal, Slot
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
from fspachinko.entrypoints.gui.constants import GUIFileDialogFilter, GUIName, GUISettingsKey, GUITitle
from fspachinko.entrypoints.gui.helpers import MENU_STRUCTURE, TOOLBAR_STRUCTURE

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent

    from fspachinko.bootstrap import FSPachinkoBootstrapper


class CentralWidget(QWidget):
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


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, bootstrapper: FSPachinkoBootstrapper) -> None:
        """Initialize the main window."""
        super().__init__()
        self.bootstrapper = bootstrapper
        self.bus = bootstrapper.build_message_bus()
        self.filesystem = bootstrapper.filesystem
        self._actions = Actions.build()
        self._original_title = ""
        self.config_path = ""
        gui_log_handler = QtLogHandler()
        self.bus.logger.add_handler("qtgui", gui_log_handler)
        self.log_signal = gui_log_handler.signals
        self.setAnimated(True)
        self.ui = CentralWidget(*(w(title, name, *args) for w, title, name, *args in get_component_map()))
        self.setCentralWidget(self.ui)
        self.log_widget = LogWidget()
        self.progress_widget = ProgressWidget()
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, BaseDockWidget(self.log_widget, "LogDock"))
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, BaseDockWidget(self.progress_widget, "ProgressDock"))
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

    def init_ui_settings(self) -> None:
        """Initialize GUI settings manager."""
        qsettings = QSettings()
        if (geometry := qsettings.value(GUISettingsKey.GEOMETRY)) and isinstance(geometry, bytes | bytearray):
            self.restoreGeometry(geometry)
        if (state := qsettings.value(GUISettingsKey.STATE)) and isinstance(state, bytes | bytearray):
            self.restoreState(state)
        if profile_path := str(qsettings.value(GUISettingsKey.CONFIG, "")):
            self.update_config_path(profile_path)
            self.ui.restore_config(self.filesystem.json_to_dict(self.config_path))

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
            self.save_config()

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
            self.ui.restore_config(self.filesystem.json_to_dict(self.config_path))

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
        config = ConfigModel.model_validate(self.ui.config)
        self.bootstrapper.configure_pipeline_for_run(config)
        self.progress_widget.handle_start_process(config.directory.count)
        self.bus.handle(
            RunTransferJob(
                root=config.root,
                max_per_dir=config.options.max_per_dir,
                unique_files_only=config.options.is_create_unique_dirs,
            ),
        )
        self.handle_finished()

    @Slot()
    def on_stop(self) -> None:
        """Stop the process."""
        self.bus.handle(StopProcess())

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
