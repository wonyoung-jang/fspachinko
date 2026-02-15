"""Main module."""

import logging

from PySide6.QtCore import QThreadPool, Slot
from PySide6.QtWidgets import QGroupBox, QWidget

from fspachinko.gui.loggers import QtLogHandler

from ..core import PERCENTAGE_100, GUIName
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
        self.thread_pool = QThreadPool()
        self.ui = UIBuilder()
        self.setLayout(self.ui.build())
        self.setup_qt_logger()

    def setup_qt_logger(self) -> None:
        """Set up the Qt logger."""
        qt_log_handler = QtLogHandler(self.ui.logging.textbrowser_log.append)
        root_logger = logging.getLogger()
        for hndl in root_logger.handlers:
            if hndl.name == "console":
                root_logger.removeHandler(hndl)
        root_logger.addHandler(qt_log_handler)

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
        self.ui.progress.reset()
        self.ui.progress.bind(self.worker.signals)
        self.ui.progress.count.connect(self.update_title_progress)
        self.ui.progress.finished.connect(self.on_finished)
        self.toggle_ui(is_enabled=False)
        self.thread_pool.start(self.worker)

    @Slot()
    def on_stop(self) -> None:
        """Stop the process."""
        if hasattr(self, "worker"):
            self.worker.stop()

    @Slot(int)
    def update_title_progress(self, val: int) -> None:
        """Update window title with progress percentage."""
        pct = int((val / self.ui.progress.progbar_dir.maximum()) * PERCENTAGE_100)
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
