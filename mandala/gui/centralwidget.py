"""Main module for Mandala."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from PySide6.QtCore import QDir, Signal, Slot
from PySide6.QtWidgets import QGroupBox, QMdiArea, QSplitter, QVBoxLayout, QWidget

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
    TransferModeWidget,
)
from .workers import RunMandalaWorker


@dataclass(slots=True)
class MandalaCentralGui(QMdiArea):
    """Main application window for Mandala."""

    update_window_title: ClassVar[Signal] = Signal(str)
    worker: RunMandalaWorker = field(init=False)
    ui_root: PathSelectorWidget = field(init=False)
    ui_dest: PathSelectorWidget = field(init=False)
    ui_filecount: FileCountWidget = field(init=False)
    ui_folders: FolderCreatorWidget = field(init=False)
    ui_filenames: FilenameSettingsWidget = field(init=False)
    ui_transfermode: TransferModeWidget = field(init=False)
    ui_keywords: DualListFilterWidget = field(init=False)
    ui_extensions: DualListFilterWidget = field(init=False)
    ui_filesize: DblRangeFilterWidget = field(init=False)
    ui_duration: DblRangeFilterWidget = field(init=False)
    ui_diversity: DiversityFilterWidget = field(init=False)
    ui_progress: ProgressWidget = field(init=False)
    ui_execution: ExecutionWidget = field(init=False)
    _window_title_before_start: str = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.setObjectName("MandalaCentralGui")
        self.setup_components()
        self.setup_layout()

    def setup_components(self) -> None:
        """Set up the main UI components."""
        # Init setup components
        self.ui_root = PathSelectorWidget("Root", "root", items=[QDir.rootPath()])
        self.ui_dest = PathSelectorWidget("Destination", "dest", items=[QDir.homePath()])
        self.ui_filecount = FileCountWidget("File Count", "filecount")
        self.ui_folders = FolderCreatorWidget("Create Folders", "folder")
        self.ui_filenames = FilenameSettingsWidget("Filenames", "filename")
        self.ui_transfermode = TransferModeWidget("Transfer Mode", "transfermode")

        # Init filter components
        self.ui_keywords = DualListFilterWidget("Keywords", "keyword")
        self.ui_extensions = DualListFilterWidget("Extensions", "extension")
        self.ui_filesize = DblRangeFilterWidget(
            "Size", "filesize", suffix_options=[s.value for s in SizeUnitEnum], mapping=SIZE_MAP
        )
        self.ui_duration = DblRangeFilterWidget(
            "Duration", "duration", suffix_options=[s.value for s in TimeUnitEnum], mapping=TIME_MAP
        )
        self.ui_diversity = DiversityFilterWidget("Diversity", "diversity")

        # Init execution components
        self.ui_progress = ProgressWidget()
        self.ui_execution = ExecutionWidget()

    def setup_layout(self) -> None:
        """Set up the main UI layouts."""
        layout = QVBoxLayout(self)
        layout.addWidget(self.ui_root)
        layout.addWidget(self.ui_dest)

        output_layout = QSplitter()
        output_layout.addWidget(self.ui_folders)
        output_layout.addWidget(self.ui_filecount)
        output_layout.addWidget(self.ui_filenames)
        output_layout.addWidget(self.ui_transfermode)

        layout.addWidget(output_layout)
        layout.addWidget(self.ui_keywords)
        layout.addWidget(self.ui_extensions)

        filter_layout = QSplitter()
        filter_layout.addWidget(self.ui_filesize)
        filter_layout.addWidget(self.ui_duration)
        filter_layout.addWidget(self.ui_diversity)

        layout.addWidget(filter_layout)
        layout.addWidget(self.ui_progress)
        layout.addWidget(self.ui_execution)

    def get_mandala_config(self) -> MandalaConfig:
        """Get the current configuration as a MandalaConfig dataclass."""
        model = MandalaConfigModel(
            root=self.ui_root.get_config(),
            dest=self.ui_dest.get_config(),
            filecount=self.ui_filecount.get_config(),
            folder=self.ui_folders.get_config(),
            filename=self.ui_filenames.get_config(),
            transfermode=self.ui_transfermode.get_config(),
            keyword=self.ui_keywords.get_config(),
            extension=self.ui_extensions.get_config(),
            filesize=self.ui_filesize.get_config(),
            duration=self.ui_duration.get_config(),
            diversity=self.ui_diversity.get_config(),
            execution=self.ui_execution.get_config(),
        )
        return MandalaConfig(**model.__dict__)

    @Slot(bool)
    def _toggle_ui(self, *, enabled: bool) -> None:
        """Lock or unlock UI elements."""
        for child in self.findChildren(QWidget):
            if isinstance(child, QGroupBox):
                child.setEnabled(enabled)

    @Slot()
    def on_start(self) -> None:
        """Start the mandala process and disable UI elements."""
        try:
            config = self.get_mandala_config()
        except ValueError:
            self.ui_execution.textbrowser_log.append("Configuration error")
            return

        self._toggle_ui(enabled=False)

        self.ui_progress.progbar_total.setValue(0)
        self.ui_progress.progbar_folder.setValue(0)

        self._window_title_before_start = self.window().windowTitle()

        self.worker = RunMandalaWorker(config=config)

        signals = self.worker.observer.signals
        prog_ui = self.ui_progress
        signals.progress_total.connect(prog_ui.progbar_total.setMaximum)
        signals.count_total.connect(prog_ui.update_total_prog)
        signals.progress.connect(prog_ui.progbar_folder.setMaximum)
        signals.log.connect(self.ui_execution.textbrowser_log.append)

        signals.count.connect(prog_ui.progbar_folder.setValue)
        signals.count.connect(self._update_title_progress)

        signals.finished.connect(self._on_finished)
        signals.finished.connect(self._reset_title)

        self.worker.start()

    @Slot()
    def on_stop(self) -> None:
        """Stop the mandala process."""
        if self.worker:
            self.worker.stop()
        self.ui_execution.textbrowser_log.append("Stop requested by user...")

    @Slot()
    def _on_finished(self) -> None:
        """Handle worker finished signal."""
        self._toggle_ui(enabled=True)

    @Slot(int)
    def _update_title_progress(self, val: int) -> None:
        curr_title = self._window_title_before_start
        max_files = self.ui_progress.progbar_folder.maximum()
        if max_files > 0:
            pct = int((val / max_files) * 100)
            self.update_window_title.emit(f"[{pct}%] {curr_title}")
        else:
            self.update_window_title.emit(f"[{val} files] {curr_title}")

    @Slot()
    def _reset_title(self) -> None:
        self.update_window_title.emit(self._window_title_before_start)
