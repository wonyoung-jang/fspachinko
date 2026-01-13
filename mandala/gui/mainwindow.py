"""Main module for Mandala."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PySide6.QtCore import QDir, Qt, QTimer, Slot
from PySide6.QtWidgets import QGridLayout, QMainWindow, QScrollArea, QStatusBar, QWidget

from ..config.constants import SizeUnitEnum, TimeUnitEnum
from ..config.schemas import MandalaConfigModel
from ..core.config import MandalaConfig
from .components import (
    DiversityFilterWidget,
    DurationFilterWidget,
    ExecutionWidget,
    ExtensionsFilterWidget,
    FileCountWidget,
    FilenameSettingsWidget,
    FilesizeFilterWidget,
    FolderCreatorWidget,
    KeywordsFilterWidget,
    PathSelectorWidget,
    TrashSettingsWidget,
)
from .settings import GuiSettingsManager
from .workers import RunMandalaWorker

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent


@dataclass(slots=True)
class MandalaMainWindow(QMainWindow):
    """Main application window for Mandala."""

    settings: GuiSettingsManager = field(default_factory=GuiSettingsManager)
    ui: MandalaCentralGui = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("Mandala: Copy random files")
        self.ui = MandalaCentralGui()

        scroll = QScrollArea(widgetResizable=True)
        scroll.setWidget(self.ui)
        self.setCentralWidget(scroll)

        self.setStatusBar(QStatusBar(self))

        self.setup_settings()
        self.ui.ui_sect_exec.signal_close.connect(self.close)

    def setup_settings(self) -> None:
        """Set up the GUI settings manager."""
        self._register_settings()
        self.restoreGeometry(self.settings.get_window_settings())
        self.settings.load_gui()

    def _register_settings(self) -> None:
        """Register GUI settings to the settings manager."""
        registry = {
            # Execution
            "show_invalid": self.ui.ui_sect_exec.chk_invalid,
            "stall_time_limit": self.ui.ui_sect_exec.dblspin_stall,
            # Paths
            "root_path": self.ui.ui_root.combo,
            "dest_path": self.ui.ui_dest.combo,
            # File Count
            "fc_fixed_val": self.ui.ui_file_count.spin_fixed,
            "fc_fixed_chk": self.ui.ui_file_count.groupbox_fixed,
            "fc_rand_chk": self.ui.ui_file_count.groupbox_rand,
            "fc_rand_min": self.ui.ui_file_count.spin_min_rand,
            "fc_rand_max": self.ui.ui_file_count.spin_max_rand,
            # Folders
            "folder_enabled": self.ui.ui_folders,
            "folder_count": self.ui.ui_folders.spinbox_folder_count,
            "folder_name": self.ui.ui_folders.lineedit_folder_name,
            "folder_unique": self.ui.ui_folders.chk_unique_folders,
            # Filenames
            "filename_enabled": self.ui.ui_filenames,
            "filename_idx": self.ui.ui_filenames.radio_index,
            "filename_rename": self.ui.ui_filenames.radio_rename,
            "filename_text": self.ui.ui_filenames.lineedit_rename,
            # Trash
            "trash_enabled": self.ui.ui_trash,
            "trash_empty": self.ui.ui_trash.chk_empty_folders,
            "trash_valid": self.ui.ui_trash.chk_valid_files,
            "trash_invalid": self.ui.ui_trash.chk_invalid_files,
            # Keywords
            "kw_filter_enabled": self.ui.ui_keywords,
            "kw_filter_text": self.ui.ui_keywords.filter_edit,
            "kw_filter_include": self.ui.ui_keywords.filter_include_radio,
            "kw_filter_exclude": self.ui.ui_keywords.filter_exclude_radio,
            # Extensions
            "ext_filter_enabled": self.ui.ui_extensions,
            "ext_filter_text": self.ui.ui_extensions.filter_edit,
            "ext_filter_include": self.ui.ui_extensions.filter_include_radio,
            "ext_filter_exclude": self.ui.ui_extensions.filter_exclude_radio,
            # File Size
            "size_enabled": self.ui.ui_filesize,
            "size_min": self.ui.ui_filesize.min_spin,
            "size_max": self.ui.ui_filesize.max_spin,
            "size_unit": self.ui.ui_filesize.combo,
            # Duration
            "dur_enabled": self.ui.ui_duration,
            "dur_min": self.ui.ui_duration.min_spin,
            "dur_max": self.ui.ui_duration.max_spin,
            "dur_unit": self.ui.ui_duration.combo,
            # Weight
            "weight_enabled": self.ui.ui_weight,
            "weight_min": self.ui.ui_weight.min_spin,
            "weight_max": self.ui.ui_weight.max_spin,
        }
        self.settings.register_widgets(registry)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Handle window close event."""
        self.settings.save_window_settings(geometry=self.saveGeometry())
        self.settings.save_gui()
        super().closeEvent(event)


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
    ui_keywords: KeywordsFilterWidget = field(init=False)
    ui_extensions: ExtensionsFilterWidget = field(init=False)
    ui_filesize: FilesizeFilterWidget = field(init=False)
    ui_duration: DurationFilterWidget = field(init=False)
    ui_weight: DiversityFilterWidget = field(init=False)
    ui_sect_exec: ExecutionWidget = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("Mandala: Copy random files")
        self.setup_components()
        self.setup_layout()
        self.setup_timer()

    def setup_components(self) -> None:
        """Set up the main UI components."""
        # Init setup components
        self.ui_root = PathSelectorWidget(title="Root", items=[QDir.rootPath()])
        self.ui_dest = PathSelectorWidget(title="Destination", items=[QDir.homePath()])
        self.ui_file_count = FileCountWidget(title="File Count")
        self.ui_folders = FolderCreatorWidget(title="Create Folders")
        self.ui_filenames = FilenameSettingsWidget(title="Filenames")
        self.ui_trash = TrashSettingsWidget(title="Trash")

        # Init filter components
        self.ui_keywords = KeywordsFilterWidget(title="Keywords")
        self.ui_extensions = ExtensionsFilterWidget(title="Extensions")
        self.ui_filesize = FilesizeFilterWidget(title="Size", suffix_options=[s.value for s in SizeUnitEnum])
        self.ui_duration = DurationFilterWidget(title="Duration", suffix_options=[s.value for s in TimeUnitEnum])
        self.ui_weight = DiversityFilterWidget(title="Weight")

        # Init sidebar and run components
        self.ui_sect_exec = ExecutionWidget()

        # Connections
        self.ui_sect_exec.signal_start.connect(self._on_start)
        self.ui_sect_exec.signal_stop.connect(self._on_stop)

    def setup_layout(self) -> None:
        """Set up the main UI layouts."""
        layout = QGridLayout(self)
        layout.addWidget(self.ui_root, 0, 0, 1, 6)
        layout.addWidget(self.ui_dest, 1, 0, 1, 6)
        layout.addWidget(self.ui_file_count, 2, 0, 1, 6)
        layout.addWidget(self.ui_folders, 3, 0, 1, 2)
        layout.addWidget(self.ui_filenames, 3, 2, 1, 2)
        layout.addWidget(self.ui_trash, 3, 4, 1, 2)
        layout.addWidget(self.ui_keywords, 4, 0, 1, 6)
        layout.addWidget(self.ui_extensions, 5, 0, 1, 6)
        layout.addWidget(self.ui_filesize, 6, 0, 1, 2)
        layout.addWidget(self.ui_duration, 6, 2, 1, 2)
        layout.addWidget(self.ui_weight, 6, 4, 1, 2)
        layout.addWidget(self.ui_sect_exec, 7, 0, 1, 6)

    def setup_timer(self) -> None:
        """Set up the timer for UI updates."""
        self.timer = QTimer(singleShot=False, timerType=Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.ui_sect_exec.update_timer)

    def get_mandala_config(self) -> MandalaConfig:
        """Get the current configuration as a MandalaConfig dataclass."""
        model = MandalaConfigModel(
            root=self.ui_root.get_config(),
            dest=self.ui_dest.get_config(),
            count_model=self.ui_file_count.get_config(),
            folders_model=self.ui_folders.get_config(),
            filename_model=self.ui_filenames.get_config(),
            trash_model=self.ui_trash.get_config(),
            keywords_model=self.ui_keywords.get_config(),
            extensions_model=self.ui_extensions.get_config(),
            size_model=self.ui_filesize.get_config(),
            duration_model=self.ui_duration.get_config(),
            diversity_model=self.ui_weight.get_config(),
            execution_model=self.ui_sect_exec.get_config(),
        )
        return MandalaConfig(**model.__dict__)

    @Slot(bool)
    def _toggle_ui(self, *, enabled: bool) -> None:
        """Lock or unlock UI elements."""
        self.ui_sect_exec.btn_start.setEnabled(enabled)
        self.ui_sect_exec.btn_stop.setEnabled(not enabled)
        for child in self.findChildren(QWidget):
            if child not in (self.ui_sect_exec, self.ui_sect_exec.btn_stop, self.ui_sect_exec.textbrowser_log):
                child.setEnabled(enabled)

    @Slot()
    def _on_start(self) -> None:
        """Start the mandala process and disable UI elements."""
        try:
            config = self.get_mandala_config()
        except ValueError:
            self.ui_sect_exec.textbrowser_log.append("Error: Invalid configuration")
            return

        self._toggle_ui(enabled=False)

        stall_limit = config.execution_model.stall_time_limit
        stall_max = int(stall_limit * 100)
        self.ui_sect_exec.progbar_main.reset()
        self.ui_sect_exec.progbar_stall.setRange(0, stall_max)
        self.ui_sect_exec.progbar_stall.setValue(stall_max)
        self.ui_sect_exec.label_stall.setText(f"{stall_limit}0 s")

        self.worker = RunMandalaWorker(config=config)
        self.worker.observer.progress.connect(self.ui_sect_exec.progbar_main.setMaximum)
        self.worker.observer.log.connect(self.ui_sect_exec.textbrowser_log.append)
        self.worker.observer.count.connect(self.ui_sect_exec.progbar_main.setValue)
        self.worker.observer.time.connect(self.ui_sect_exec.reset_stall_timer_display)
        self.worker.observer.finished.connect(self._on_finished)

        self.timer.start(10)
        self.worker.start()

    @Slot()
    def _on_stop(self) -> None:
        """Stop the mandala process."""
        if self.worker:
            self.worker.stop()
        self.ui_sect_exec.textbrowser_log.append("Stop requested by user...")

    @Slot()
    def _on_finished(self) -> None:
        """Handle worker finished signal."""
        self.timer.stop()
        self._toggle_ui(enabled=True)
