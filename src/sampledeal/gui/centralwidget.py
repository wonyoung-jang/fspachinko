"""Main module."""

import logging
from dataclasses import dataclass, field

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QGroupBox, QWidget

from ..utils import PERCENTAGE_100, GUIName
from .components import ProgressBinder
from .qthelpers import set_qt_name
from .uibuilder import UIBuilder
from .workers import MainThread, MainWorker, WorkerSignals

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CentralWidget(QWidget):
    """Main application window."""

    thread: MainThread | None = None
    ui: UIBuilder = field(default_factory=UIBuilder)
    progress_binder: ProgressBinder = field(init=False)
    window_title_original: str = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        set_qt_name(self, GUIName.CENTRAL_WIDGET)
        layout = self.ui.build_layout()
        self.setLayout(layout)
        self.progress_binder = ProgressBinder(self.ui.progress, self.ui.logging)

    @Slot()
    def on_start(self) -> None:
        """Start the process and disable UI elements."""
        try:
            config = self.ui.get_config()
        except Exception:
            logger.exception("")
            return

        self.thread = MainThread(MainWorker.from_config(config, WorkerSignals()))
        self.ui.progress.reset()
        self.window_title_original = self.window().windowTitle()
        self.progress_binder.bind(self.thread.worker.signals)
        self.progress_binder.count.connect(self.update_title_progress)
        self.progress_binder.finished.connect(self.on_finished)
        self.toggle_ui(is_enabled=False)
        self.thread.start()

    @Slot()
    def on_stop(self) -> None:
        """Stop the process."""
        if self.thread and self.thread.isRunning():
            self.thread.stop()

    @Slot(int)
    def update_title_progress(self, val: int) -> None:
        """Update window title with progress percentage."""
        pct = int((val / self.ui.progress.progbar_folder.maximum()) * PERCENTAGE_100)
        self.window().setWindowTitle(f"[{pct}%] {self.window_title_original}")

    @Slot()
    def on_finished(self) -> None:
        """Handle worker finished signal."""
        self.toggle_ui(is_enabled=True)
        self.window().setWindowTitle(self.window_title_original)

    def toggle_ui(self, *, is_enabled: bool) -> None:
        """Lock or unlock UI elements."""
        for child in self.findChildren(QGroupBox):
            child.setEnabled(is_enabled)
