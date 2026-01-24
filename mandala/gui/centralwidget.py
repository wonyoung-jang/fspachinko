"""Main module for Mandala."""

from dataclasses import dataclass, field
from typing import ClassVar

from PySide6.QtCore import QDir, Signal, Slot
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..config import MandalaConfigModel
from ..utils import PERCENTAGE_100, SIZE_MAP, TIME_MAP, ByteUnit, TimeUnit
from .components import (
    DblRangeFilterWidget,
    DiversityFilterWidget,
    DualListFilterWidget,
    FileCountWidget,
    FilenameWidget,
    FolderCreatorWidget,
    LoggingWidget,
    PathSelectorWidget,
    ProgressWidget,
    TransferModeWidget,
    WalkerWidget,
)
from .qthelpers import init_widget
from .workers import MandalaThread, MandalaWorker, WorkerSignals


@dataclass(slots=True)
class MandalaCentralGui(QWidget):
    """Main application window for Mandala."""

    thread: MandalaThread = field(init=False)
    ui_root: PathSelectorWidget = field(init=False)
    ui_dest: PathSelectorWidget = field(init=False)
    ui_filecount: FileCountWidget = field(init=False)
    ui_folders: FolderCreatorWidget = field(init=False)
    ui_filename: FilenameWidget = field(init=False)
    ui_transfermode: TransferModeWidget = field(init=False)
    ui_keywords: DualListFilterWidget = field(init=False)
    ui_extensions: DualListFilterWidget = field(init=False)
    ui_filesize: DblRangeFilterWidget = field(init=False)
    ui_duration: DblRangeFilterWidget = field(init=False)
    ui_diversity: DiversityFilterWidget = field(init=False)
    ui_progress: ProgressWidget = field(init=False)
    ui_logging: LoggingWidget = field(init=False)
    ui_walker: WalkerWidget = field(init=False)
    _window_title_before_start: str = field(init=False)

    update_window_title: ClassVar[Signal] = Signal(str)

    def __post_init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        init_widget(self, "MandalaCentralGui")
        self.init_components()
        self.init_layout()

    def init_components(self) -> None:
        """Set up the main UI components."""
        # Init setup components
        self.ui_root = PathSelectorWidget("Root", "root", items=[QDir.rootPath()])
        self.ui_dest = PathSelectorWidget("Destination", "dest", items=[QDir.homePath()])
        self.ui_filecount = FileCountWidget()
        self.ui_folders = FolderCreatorWidget()
        self.ui_filename = FilenameWidget()
        self.ui_transfermode = TransferModeWidget()

        # Init filter components
        self.ui_keywords = DualListFilterWidget("Keywords", "keyword")
        self.ui_extensions = DualListFilterWidget("Extensions", "extension")
        self.ui_filesize = DblRangeFilterWidget("Size", "filesize", items=tuple(ByteUnit), mapping=SIZE_MAP)
        self.ui_duration = DblRangeFilterWidget("Duration", "duration", items=tuple(TimeUnit), mapping=TIME_MAP)
        self.ui_diversity = DiversityFilterWidget()
        self.ui_walker = WalkerWidget()

        # Init execution components
        self.ui_progress = ProgressWidget()
        self.ui_logging = LoggingWidget()

    def init_layout(self) -> None:
        """Set up the main UI layouts."""
        layout = QVBoxLayout(self)
        layout.addWidget(self.ui_root)
        layout.addWidget(self.ui_dest)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.ui_folders)
        output_layout.addWidget(self.ui_filecount)
        output_layout.addWidget(self.ui_filename)
        output_layout.addWidget(self.ui_transfermode)

        layout.addLayout(output_layout)
        layout.addWidget(self.ui_keywords)
        layout.addWidget(self.ui_extensions)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.ui_filesize)
        filter_layout.addWidget(self.ui_duration)
        filter_layout.addWidget(self.ui_diversity)
        filter_layout.addWidget(self.ui_walker)

        layout.addLayout(filter_layout)
        layout.addWidget(self.ui_progress)
        layout.addWidget(self.ui_logging)

    def get_config(self) -> MandalaConfigModel:
        """Get the current configuration as a MandalaConfig dataclass."""
        return MandalaConfigModel(
            root=self.ui_root.get_config(),
            dest=self.ui_dest.get_config(),
            filecount=self.ui_filecount.get_config(),
            folder=self.ui_folders.get_config(),
            filename=self.ui_filename.get_config(),
            transfermode=self.ui_transfermode.get_config(),
            keyword=self.ui_keywords.get_config(),
            extension=self.ui_extensions.get_config(),
            filesize=self.ui_filesize.get_config(),
            duration=self.ui_duration.get_config(),
            diversity=self.ui_diversity.get_config(),
            walker=self.ui_walker.get_config(),
        )

    def toggle_ui(self, *, enabled: bool) -> None:
        """Lock or unlock UI elements."""
        for child in self.findChildren(QWidget):
            if child.objectName() in {"logging"}:
                continue
            child.setEnabled(enabled)

    @Slot()
    def on_start(self) -> None:
        """Start the mandala process and disable UI elements."""
        try:
            config = self.get_config()
        except ValueError:
            self.ui_logging.textbrowser_log.append("Configuration error")
            return

        self.ui_progress.reset()
        self._window_title_before_start = self.window().windowTitle()
        self.toggle_ui(enabled=False)

        self.thread = MandalaThread(MandalaWorker.from_config(config, WorkerSignals()))
        self.setup_thread_signals()
        self.thread.start()

    def setup_thread_signals(self) -> None:
        """Set up thread signals."""
        signals = self.thread.worker.signals
        signals.progress_total.connect(self.ui_progress.progbar_total.setMaximum)
        signals.count_total.connect(self.ui_progress.update_total_prog)
        signals.progress.connect(self.ui_progress.progbar_folder.setMaximum)
        signals.log.connect(self.ui_logging.textbrowser_log.append)
        signals.count.connect(self.ui_progress.progbar_folder.setValue)
        signals.count.connect(self.update_title_progress)
        signals.finished.connect(self.on_finished)

    @Slot()
    def on_stop(self) -> None:
        """Stop the mandala process."""
        if hasattr(self, "thread") and self.thread.isRunning():
            self.ui_logging.textbrowser_log.append("Stop requested by user...")
            self.thread.stop()

    @Slot()
    def on_finished(self) -> None:
        """Handle worker finished signal."""
        self.toggle_ui(enabled=True)
        self.reset_title()

    @Slot(int)
    def update_title_progress(self, val: int) -> None:
        """Update window title with progress percentage."""
        curr_title = self._window_title_before_start
        max_files = self.ui_progress.progbar_folder.maximum()
        if max_files:
            pct = int((val / max_files) * PERCENTAGE_100)
            self.update_window_title.emit(f"[{pct}%] {curr_title}")
        else:
            self.update_window_title.emit(f"[{val} files] {curr_title}")

    @Slot()
    def reset_title(self) -> None:
        """Reset window title to original."""
        self.update_window_title.emit(self._window_title_before_start)
