"""Main module."""

from PySide6.QtCore import QThreadPool, Signal, Slot
from PySide6.QtWidgets import QWidget

from ..configuration.model import get_config_from_pydict
from .loggers_gui import setup_gui_logger
from .uibuilder import UIBuilder
from .workers import MainWorker


class CentralWidget(QWidget):
    """Main application window."""

    title_changed = Signal(str)

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.original_window_title = ""
        self.worker: MainWorker | None = None
        self.thread_pool = QThreadPool()
        self.ui = UIBuilder()
        self.setLayout(self.ui.build())
        setup_gui_logger(self.ui.log_append)

    @property
    def config(self) -> dict:
        """Capture the current configuration from the UI."""
        return self.ui.config

    def restore_config(self, config: dict) -> None:
        """Restore the configuration to the UI."""
        self.ui.restore(config)

    @Slot()
    def on_start(self) -> None:
        """Start the process and disable UI elements."""
        self.original_window_title = self.window().windowTitle()
        self.worker = MainWorker()
        self.worker.signals.process_started.connect(self.handle_start_process)
        self.worker.signals.directory_started.connect(self.handle_directory_start)
        self.worker.signals.file_transferred.connect(self.handle_file_transfer)
        self.worker.signals.finished.connect(self.handle_finished)
        self.thread_pool.start(self.run_worker)

    def run_worker(self) -> None:
        """Run the worker in a separate thread."""
        if self.worker is not None:
            config_model = get_config_from_pydict(self.config)
            self.worker.run(config_model)

    @Slot()
    def on_stop(self) -> None:
        """Stop the process."""
        if self.worker is not None:
            self.worker.stop()

    @Slot(int)
    def handle_start_process(self, dir_count: int) -> None:
        """Handle the start of the process."""
        self.ui.toggle(is_enabled=False)
        self.ui.handle_start_process(dir_count)

    @Slot(int)
    def handle_directory_start(self, target: int) -> None:
        """Update the directory progress bar."""
        self.ui.handle_directory_start(target)

    @Slot()
    def handle_file_transfer(self) -> None:
        """Update the window title with the current progress."""
        percentage = self.ui.handle_file_transfer()
        self.title_changed.emit(f"[{percentage}%] {self.original_window_title}")

    @Slot()
    def handle_finished(self) -> None:
        """Reset the window title to the original."""
        self.ui.toggle(is_enabled=True)
        self.title_changed.emit(self.original_window_title)
