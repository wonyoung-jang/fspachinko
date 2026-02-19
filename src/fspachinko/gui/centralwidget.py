"""Main module."""

import logging

from PySide6.QtCore import QThreadPool, Slot
from PySide6.QtWidgets import QGroupBox, QWidget

from ..core import PERCENTAGE_100, GUIName
from .loggers import setup_gui_logger
from .qthelpers import set_qt_name
from .uibuilder import UIBuilder
from .workers import MainWorker

logger = logging.getLogger(__name__)


class CentralWidget(QWidget):
    """Main application window."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        set_qt_name(self, GUIName.CENTRAL_WIDGET)
        self.original_window_title = ""
        self.worker = None
        self.thread_pool = QThreadPool()
        self.ui = UIBuilder()
        self.setLayout(self.ui.build())
        setup_gui_logger(self.ui.logging.textbrowser_log.append)

    @Slot()
    def on_start(self) -> None:
        """Start the process and disable UI elements."""
        try:
            config = self.ui.get_config()
        except Exception:
            logger.exception("Failed to get configuration from UI.")
            return

        self.worker = MainWorker(config)
        self.original_window_title = self.window().windowTitle()
        signals = self.worker.signals
        progress = self.ui.progress
        progress.reset()
        signals.start_process.connect(progress.progbar_dirs.setMaximum)
        signals.file_transferred.connect(progress.progbar_files.setValue)
        signals.directory_start.connect(progress.start_directory)
        signals.file_transferred.connect(self.update_title_progress)
        signals.finished.connect(self.on_finished)
        self.toggle_ui(is_enabled=False)
        self.thread_pool.start(self.worker)

    @Slot()
    def on_stop(self) -> None:
        """Stop the process."""
        if self.worker:
            self.worker.stop()

    @Slot(int)
    def update_title_progress(self, val: int) -> None:
        """Update window title with progress percentage."""
        pct = int(val * PERCENTAGE_100 / self.ui.progress.progbar_files.maximum())
        self.window().setWindowTitle(f"[{pct}%] {self.original_window_title}")

    @Slot()
    def on_finished(self) -> None:
        """Handle worker finished signal."""
        self.toggle_ui(is_enabled=True)
        self.window().setWindowTitle(self.original_window_title)

    def toggle_ui(self, *, is_enabled: bool) -> None:
        """Lock or unlock UI elements."""
        for child in self.findChildren(QGroupBox):
            child.setEnabled(is_enabled)
