"""Main module."""

from PySide6.QtCore import QThreadPool, Slot
from PySide6.QtWidgets import QGroupBox, QWidget

from ..config import get_config_from_pydict
from .loggers_gui import setup_gui_logger
from .uibuilder import UIBuilder
from .workers import MainWorker


class CentralWidget(QWidget):
    """Main application window."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.original_window_title = ""
        self.worker: MainWorker | None = None
        self.thread_pool = QThreadPool()
        self.ui = UIBuilder()
        self._window = self.window()
        self.setLayout(self.ui.build())
        setup_gui_logger(self.ui.log_append)

    def toggle_ui(self, *, is_enabled: bool) -> None:
        """Lock or unlock UI elements."""
        for child in self.findChildren(QGroupBox):
            child.setEnabled(is_enabled)

    def capture_config(self) -> dict:
        """Capture the current configuration from the UI."""
        return self.ui.config

    def restore_config(self, config: dict) -> None:
        """Restore the configuration to the UI."""
        for component in self.ui.has_config:
            component.restore(config)

    @Slot()
    def on_start(self) -> None:
        """Start the process and disable UI elements."""
        self._window = self.window()
        self.original_window_title = self._window.windowTitle()
        config_model = get_config_from_pydict(self.ui.config)
        self.worker = MainWorker(config_model)
        self.worker.signals.start_process.connect(self.handle_start_process)
        self.worker.signals.directory_start.connect(self.handle_directory_start)
        self.worker.signals.file_transferred.connect(self.handle_file_transfer)
        self.worker.signals.finished.connect(self.handle_finished)
        self.thread_pool.start(self.worker)

    @Slot()
    def on_stop(self) -> None:
        """Stop the process."""
        if self.worker is not None:
            self.worker.stop()

    @Slot(int)
    def handle_start_process(self, dir_count: int) -> None:
        """Handle the start of the process."""
        self.toggle_ui(is_enabled=False)
        self.ui.handle_start_process(dir_count)

    @Slot(int)
    def handle_directory_start(self, target: int) -> None:
        """Update the directory progress bar."""
        self.ui.handle_directory_start(target)

    @Slot()
    def handle_file_transfer(self) -> None:
        """Update the window title with the current progress."""
        percentage = self.ui.handle_file_transfer()
        self._window.setWindowTitle(f"[{percentage}%] {self.original_window_title}")

    @Slot()
    def handle_finished(self) -> None:
        """Reset the window title to the original."""
        self.toggle_ui(is_enabled=True)
        self._window.setWindowTitle(self.original_window_title)
