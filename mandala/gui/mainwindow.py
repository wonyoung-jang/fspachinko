"""Main module for Mandala."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PySide6.QtCore import QDir, Qt, QTimer, Slot
from PySide6.QtWidgets import QGridLayout, QMainWindow, QStatusBar, QWidget

from ..config.schemas import MandalaConfigModel
from ..core.config import MandalaConfig
from .components import (
    DestPathSelectorWidget,
    DurationFilterWidget,
    ExecutionWidget,
    ExtensionsFilterWidget,
    FileCountWidget,
    FilenameSettingsWidget,
    FilesizeFilterWidget,
    FolderCreatorWidget,
    KeywordsFilterWidget,
    RootPathSelectorWidget,
    TrashSettingsWidget,
    WeightFilterWidget,
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
        self.setCentralWidget(self.ui)
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
            # Sidebar
            "show_invalid": self.ui.ui_sect_exec.chk_invalid,
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
            # "kw_inc_chk": self.ui.ui_keywords.include_groupbox,
            # "kw_inc_text": self.ui.ui_keywords.include_edit,
            # "kw_exc_chk": self.ui.ui_keywords.exclude_groupbox,
            # "kw_exc_text": self.ui.ui_keywords.exclude_edit,
            # Extensions
            "ext_filter_enabled": self.ui.ui_extensions,
            "ext_filter_text": self.ui.ui_extensions.filter_edit,
            "ext_filter_include": self.ui.ui_extensions.filter_include_radio,
            "ext_filter_exclude": self.ui.ui_extensions.filter_exclude_radio,
            # "ext_inc_chk": self.ui.ui_extensions.include_groupbox,
            # "ext_inc_text": self.ui.ui_extensions.include_edit,
            # "ext_exc_chk": self.ui.ui_extensions.exclude_groupbox,
            # "ext_exc_text": self.ui.ui_extensions.exclude_edit,
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
    ui_root: RootPathSelectorWidget = field(init=False)
    ui_dest: DestPathSelectorWidget = field(init=False)
    ui_file_count: FileCountWidget = field(init=False)
    ui_folders: FolderCreatorWidget = field(init=False)
    ui_filenames: FilenameSettingsWidget = field(init=False)
    ui_trash: TrashSettingsWidget = field(init=False)
    ui_keywords: KeywordsFilterWidget = field(init=False)
    ui_extensions: ExtensionsFilterWidget = field(init=False)
    ui_filesize: FilesizeFilterWidget = field(init=False)
    ui_duration: DurationFilterWidget = field(init=False)
    ui_weight: WeightFilterWidget = field(init=False)
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
        self.ui_root = RootPathSelectorWidget(title="Root", items=[QDir.rootPath()])
        self.ui_dest = DestPathSelectorWidget(title="Destination", items=[QDir.homePath()])
        self.ui_file_count = FileCountWidget(title="File Count")
        self.ui_folders = FolderCreatorWidget(title="Create Folders")
        self.ui_filenames = FilenameSettingsWidget(title="Filenames")
        self.ui_trash = TrashSettingsWidget(title="Trash")

        # Init filter components
        self.ui_keywords = KeywordsFilterWidget(title="Keywords")
        self.ui_extensions = ExtensionsFilterWidget(title="Extensions")
        self.ui_filesize = FilesizeFilterWidget(title="Size", suffix_options=("B", "KB", "MB", "GB"))
        self.ui_duration = DurationFilterWidget(title="Duration", suffix_options=("s", "m"))
        self.ui_weight = WeightFilterWidget(title="Weight")

        # Init sidebar and run components
        self.ui_sect_exec = ExecutionWidget()

        # Connections
        self.ui_sect_exec.signal_start.connect(self._start_on_push)
        self.ui_sect_exec.signal_stop.connect(self._stop_on_push)

    def setup_layout(self) -> None:
        """Set up the main UI layouts."""
        # Layout setup components
        ui_sect_setup = QWidget()
        l_setup = QGridLayout(ui_sect_setup)
        l_setup.addWidget(self.ui_root, 0, 0, 1, 6)
        l_setup.addWidget(self.ui_dest, 1, 0, 1, 6)
        l_setup.addWidget(self.ui_file_count, 2, 0, 1, 6)
        l_setup.addWidget(self.ui_folders, 3, 0, 1, 2)
        l_setup.addWidget(self.ui_filenames, 3, 2, 1, 2)
        l_setup.addWidget(self.ui_trash, 3, 4, 1, 2)

        # Layout filter components
        ui_sect_filter = QWidget()
        l_filter = QGridLayout(ui_sect_filter)
        l_filter.addWidget(self.ui_keywords, 0, 0, 1, 3)
        l_filter.addWidget(self.ui_extensions, 1, 0, 1, 3)
        l_filter.addWidget(self.ui_filesize, 2, 0)
        l_filter.addWidget(self.ui_duration, 2, 1)
        l_filter.addWidget(self.ui_weight, 2, 2)

        # Main layout
        layout = QGridLayout(self)
        layout.addWidget(ui_sect_setup, 0, 0)
        layout.addWidget(ui_sect_filter, 1, 0)
        layout.addWidget(self.ui_sect_exec, 2, 0)

    def setup_timer(self) -> None:
        """Set up the timer for UI updates."""
        self.timer = QTimer(singleShot=False, timerType=Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.ui_sect_exec.update_timer)

    def get_mandala_config(self) -> MandalaConfig:
        """Get the current configuration as a MandalaConfig dataclass."""
        model = MandalaConfigModel(
            **self.ui_root.get_config(),
            **self.ui_dest.get_config(),
            **self.ui_file_count.get_config(),
            **self.ui_keywords.get_config(),
            **self.ui_extensions.get_config(),
            **self.ui_filesize.get_config(),
            **self.ui_duration.get_config(),
            **self.ui_weight.get_config(),
            **self.ui_folders.get_config(),
            **self.ui_filenames.get_config(),
            **self.ui_trash.get_config(),
            **self.ui_sect_exec.get_config(),
        )
        return MandalaConfig(**model.model_dump())

    @Slot(bool)
    def _toggle_ui(self, *, enabled: bool) -> None:
        """Lock or unlock UI elements."""
        self.ui_sect_exec.btn_start.setEnabled(enabled)
        self.ui_sect_exec.btn_stop.setEnabled(not enabled)

        # Disable all inputs while running
        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QWidget) and name not in ("ui_sect_exec", "btn_stop", "textbrowser_log"):
                obj.setEnabled(enabled)

    @Slot()
    def _start_on_push(self) -> None:
        """Start the mandala process and disable UI elements."""
        try:
            config = self.get_mandala_config()
        except ValueError:
            self.ui_sect_exec.textbrowser_log.append("Error: Invalid configuration")
            return

        self._toggle_ui(enabled=False)

        self.ui_sect_exec.progbar_main.reset()
        self.ui_sect_exec.progbar_stall.setRange(0, int(config.stall_time_limit * 100))
        self.ui_sect_exec.progbar_stall.setValue(self.ui_sect_exec.progbar_stall.maximum())
        self.ui_sect_exec.label_stall.setText(f"{config.stall_time_limit}0 s")

        self.worker = RunMandalaWorker(config=config)
        self.worker.observer.log.connect(self.ui_sect_exec.textbrowser_log.append)
        self.worker.observer.count.connect(self.ui_sect_exec.progbar_main.setValue)
        self.worker.observer.time.connect(self.ui_sect_exec.reset_stall_timer_display)
        self.worker.observer.finished.connect(self._stop_on_worker_finished)

        self.timer.start(10)
        self.worker.start()

    @Slot()
    def _stop_on_push(self) -> None:
        """Stop the mandala process."""
        self.ui_sect_exec.textbrowser_log.append("Stop requested by user...")
        if self.worker:
            self.worker.stop()

    @Slot()
    def _stop_on_worker_finished(self) -> None:
        """Handle worker finished signal."""
        self.timer.stop()
        self._toggle_ui(enabled=True)
