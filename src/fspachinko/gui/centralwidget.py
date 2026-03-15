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
        self.worker = None
        self.thread_pool = QThreadPool()
        self.ui = UIBuilder()
        self.setLayout(self.ui.build())
        setup_gui_logger(self.ui.logging.textbrowser_log.append)

    @Slot()
    def on_start(self) -> None:
        """Start the process and disable UI elements."""
        self.original_window_title = self.window().windowTitle()
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
        if self.worker:
            self.worker.stop()

    def toggle_ui(self, *, is_enabled: bool) -> None:
        """Lock or unlock UI elements."""
        for child in self.findChildren(QGroupBox):
            child.setEnabled(is_enabled)

    @Slot(int)
    def handle_start_process(self, dir_count: int) -> None:
        """Handle the start of the process."""
        self.toggle_ui(is_enabled=False)
        self.ui.progress.progbar_dirs.setMaximum(dir_count)
        self.ui.progress.progbar_dirs.setValue(0)
        self.ui.progress.progbar_files.setValue(0)

    @Slot(int)
    def handle_directory_start(self, target: int) -> None:
        """Update the directory progress bar."""
        curr_dir_idx = self.ui.progress.progbar_dirs.value()
        self.ui.progress.progbar_dirs.setValue(curr_dir_idx + 1)
        self.ui.progress.progbar_files.setMaximum(target)
        self.ui.progress.progbar_files.setValue(0)

    @Slot()
    def handle_file_transfer(self) -> None:
        """Update the window title with the current progress."""
        curr_file_count = self.ui.progress.progbar_files.value()
        self.ui.progress.progbar_files.setValue(curr_file_count + 1)

        percentage = int((curr_file_count + 1) * 100 / self.ui.progress.progbar_files.maximum())
        self.window().setWindowTitle(f"[{percentage}%] {self.original_window_title}")

    @Slot()
    def handle_finished(self) -> None:
        """Reset the window title to the original."""
        self.toggle_ui(is_enabled=True)
        self.window().setWindowTitle(self.original_window_title)
