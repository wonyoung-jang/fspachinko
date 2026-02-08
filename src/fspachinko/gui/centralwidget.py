"""Main module."""

import logging

from PySide6.QtCore import QThreadPool, Slot
from PySide6.QtWidgets import QGroupBox, QWidget

from ..utils import PERCENTAGE_100, GUIName
from .components import ProgressBinder
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
        self.threadpool: QThreadPool = QThreadPool()
        self.ui = UIBuilder()
        layout = self.ui.build_layout()
        self.setLayout(layout)
        self.progress_binder = ProgressBinder(self.ui.progress, self.ui.logging)
        self.original_window_title = ""

    @Slot()
    def on_start(self) -> None:
        """Start the process and disable UI elements."""
        try:
            config = self.ui.get_config()
        except Exception:
            logger.exception("")
            return

        self.worker = MainWorker.from_config(config)
        self.ui.progress.reset()
        self.original_window_title = self.window().windowTitle()
        self.progress_binder.bind(self.worker.signals)
        self.progress_binder.count.connect(self.update_title_progress)
        self.progress_binder.finished.connect(self.on_finished)
        self.toggle_ui(is_enabled=False)
        self.threadpool.start(self.worker)

    @Slot()
    def on_stop(self) -> None:
        """Stop the process."""
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
