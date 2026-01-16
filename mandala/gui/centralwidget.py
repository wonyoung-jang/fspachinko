"""Main module for Mandala."""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QDir, Qt, QTimer, Slot
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from mandala.utils.constants import SIZE_MAP

from ..config.config import MandalaConfig
from ..config.schemas import MandalaConfigModel
from ..utils.constants import TIME_MAP, SizeUnitEnum, TimeUnitEnum
from .components import (
    DblRangeFilterWidget,
    DiversityFilterWidget,
    DualListFilterWidget,
    ExecutionWidget,
    FileCountWidget,
    FilenameSettingsWidget,
    FolderCreatorWidget,
    PathSelectorWidget,
    ProgressWidget,
    TrashSettingsWidget,
)
from .workers import RunMandalaWorker


@dataclass(slots=True)
class MandalaCentralGui(QWidget):
    """Main application window for Mandala."""

    worker: RunMandalaWorker = field(init=False)
    timer: QTimer = field(init=False)
    ui_root: PathSelectorWidget = field(init=False)
    ui_dest: PathSelectorWidget = field(init=False)
    ui_file_count: FileCountWidget = field(init=False)
    ui_folders: FolderCreatorWidget = field(init=False)
    ui_filenames: FilenameSettingsWidget = field(init=False)
    ui_trash: TrashSettingsWidget = field(init=False)
    ui_keywords: DualListFilterWidget = field(init=False)
    ui_extensions: DualListFilterWidget = field(init=False)
    ui_filesize: DblRangeFilterWidget = field(init=False)
    ui_duration: DblRangeFilterWidget = field(init=False)
    ui_weight: DiversityFilterWidget = field(init=False)
    ui_progress: ProgressWidget = field(init=False)
    ui_execution: ExecutionWidget = field(init=False)
    _window_title_before_start: str = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.setup_components()
        self.setup_layout()
        self.setup_timer()

    def setup_components(self) -> None:
        """Set up the main UI components."""
        # Init setup components
        self.ui_root = PathSelectorWidget("Root", "root", items=[QDir.rootPath()])
        self.ui_dest = PathSelectorWidget("Destination", "dest", items=[QDir.homePath()])
        self.ui_file_count = FileCountWidget("File Count", "filecount")
        self.ui_folders = FolderCreatorWidget("Create Folders", "folder")
        self.ui_filenames = FilenameSettingsWidget("Filenames", "filename")
        self.ui_trash = TrashSettingsWidget("Trash", "trash")

        # Init filter components
        self.ui_keywords = DualListFilterWidget("Keywords", "keyword")
        self.ui_extensions = DualListFilterWidget("Extensions", "extension")
        self.ui_filesize = DblRangeFilterWidget(
            "Size", "filesize", suffix_options=[s.value for s in SizeUnitEnum], mapping=SIZE_MAP
        )
        self.ui_duration = DblRangeFilterWidget(
            "Duration", "duration", suffix_options=[s.value for s in TimeUnitEnum], mapping=TIME_MAP
        )
        self.ui_weight = DiversityFilterWidget("Diversity", "diversity")

        # Init execution components
        self.ui_progress = ProgressWidget()
        self.ui_execution = ExecutionWidget()
        self.ui_execution.start.connect(self._on_start)
        self.ui_execution.stop.connect(self._on_stop)

    def setup_layout(self) -> None:
        """Set up the main UI layouts."""
        layout = QVBoxLayout(self)
        layout.addWidget(self.ui_root)
        layout.addWidget(self.ui_dest)

        output_layout = QSplitter()
        output_layout.addWidget(self.ui_file_count)
        output_layout.addWidget(self.ui_folders)
        output_layout.addWidget(self.ui_filenames)
        output_layout.addWidget(self.ui_trash)

        layout.addWidget(output_layout)
        layout.addWidget(self.ui_keywords)
        layout.addWidget(self.ui_extensions)

        filter_layout = QSplitter()
        filter_layout.addWidget(self.ui_filesize)
        filter_layout.addWidget(self.ui_duration)
        filter_layout.addWidget(self.ui_weight)

        layout.addWidget(filter_layout)
        layout.addWidget(self.ui_progress)
        layout.addWidget(self.ui_execution)

    def setup_timer(self) -> None:
        """Set up the timer for UI updates."""
        self.timer = QTimer(singleShot=False, timerType=Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.ui_progress.update_stall_prog)

    def get_mandala_config(self) -> MandalaConfig:
        """Get the current configuration as a MandalaConfig dataclass."""
        model = MandalaConfigModel(
            root=self.ui_root.get_config(),
            dest=self.ui_dest.get_config(),
            filecount=self.ui_file_count.get_config(),
            folder=self.ui_folders.get_config(),
            filename=self.ui_filenames.get_config(),
            trash=self.ui_trash.get_config(),
            keyword=self.ui_keywords.get_config(),
            extension=self.ui_extensions.get_config(),
            filesize=self.ui_filesize.get_config(),
            duration=self.ui_duration.get_config(),
            diversity=self.ui_weight.get_config(),
            progress=self.ui_progress.get_config(),
            execution=self.ui_execution.get_config(),
        )
        return MandalaConfig(**model.__dict__)

    @Slot(bool)
    def _toggle_ui(self, *, enabled: bool) -> None:
        """Lock or unlock UI elements."""
        self.ui_execution.btn_stop.setEnabled(not enabled)
        for child in self.findChildren(QWidget):
            if child not in (
                self.ui_execution,
                self.ui_execution.btn_stop,
                self.ui_execution.textbrowser_log,
                self.ui_progress,
                self.ui_progress.progbar_total,
                self.ui_progress.progbar_folder,
                self.ui_progress.progbar_stall,
            ):
                child.setEnabled(enabled)

    @Slot()
    def _on_start(self) -> None:
        """Start the mandala process and disable UI elements."""
        try:
            config = self.get_mandala_config()
        except ValueError:
            self.ui_execution.textbrowser_log.append("Error: Invalid configuration")
            return

        self._toggle_ui(enabled=False)

        stall_limit = config.progress.stall_time_limit
        stall_max = int(stall_limit * 100)

        self.ui_progress.progbar_total.setValue(0)
        self.ui_progress.progbar_folder.setValue(0)
        self.ui_progress.progbar_stall.setRange(0, stall_max)
        self.ui_progress.progbar_stall.setValue(stall_max)

        self._window_title_before_start = self.window().windowTitle()

        self.worker = RunMandalaWorker(config=config)

        w_signals = self.worker.observer.signals
        w_signals.progress_total.connect(self.ui_progress.progbar_total.setMaximum)
        w_signals.count_total.connect(self.ui_progress.update_total_prog)
        w_signals.progress.connect(self.ui_progress.progbar_folder.setMaximum)
        w_signals.log.connect(self.ui_execution.textbrowser_log.append)

        w_signals.count.connect(self.ui_progress.progbar_folder.setValue)
        w_signals.count.connect(self._update_title_progress)

        w_signals.time.connect(self.ui_progress.reset_stall_prog)

        w_signals.finished.connect(self._on_finished)
        w_signals.finished.connect(self._reset_title)

        self.timer.start(10)

        self.worker.start()

    @Slot()
    def _on_stop(self) -> None:
        """Stop the mandala process."""
        if self.worker:
            self.worker.stop()
        self.ui_execution.textbrowser_log.append("Stop requested by user...")

    @Slot()
    def _on_finished(self) -> None:
        """Handle worker finished signal."""
        self.timer.stop()
        self._toggle_ui(enabled=True)

    @Slot(int)
    def _update_title_progress(self, val: int) -> None:
        curr_title = self._window_title_before_start
        max_files = self.ui_progress.progbar_folder.maximum()
        if max_files > 0:
            pct = int((val / max_files) * 100)
            self.window().setWindowTitle(f"[{pct}%] {curr_title}")
        else:
            self.window().setWindowTitle(f"[{val} files] {curr_title}")

    @Slot()
    def _reset_title(self) -> None:
        self.window().setWindowTitle(self._window_title_before_start)
