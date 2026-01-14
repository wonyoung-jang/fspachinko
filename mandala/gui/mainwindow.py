"""Main module for Mandala."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QDir, QSettings, Qt, QTimer, Slot
from PySide6.QtWidgets import QFileDialog, QGridLayout, QMainWindow, QStatusBar, QToolBar, QWidget

from mandala.gui.components import ProgressWidget

from ..config.constants import SizeUnitEnum, TimeUnitEnum
from ..config.schemas import MandalaConfigModel
from ..core.config import MandalaConfig
from .components import (
    DiversityFilterWidget,
    DualListFilterWidget,
    DurationFilterWidget,
    ExecutionWidget,
    FileCountWidget,
    FilenameSettingsWidget,
    FilesizeFilterWidget,
    FolderCreatorWidget,
    PathSelectorWidget,
    TrashSettingsWidget,
)
from .settings import ProfileManager
from .workers import RunMandalaWorker

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent


@dataclass(slots=True)
class MandalaMainWindow(QMainWindow):
    """Main application window for Mandala."""

    ui: MandalaCentralGui = field(init=False)
    profiles: ProfileManager = field(init=False)
    current_profile: str = field(default="")
    qsettings: QSettings = field(default_factory=QSettings)

    def __post_init__(self) -> None:
        """Initialize the main window."""
        super().__init__()

        self.ui = MandalaCentralGui()
        self.setCentralWidget(self.ui)

        self.init_toolbar()
        self.init_menubar()
        self.init_statusbar()

        self.profiles = ProfileManager()
        self.init_settings()

        self.ui.ui_sect_exec.signal_close.connect(self.close)

        self.setWindowTitle(f"{Path(self.current_profile).stem} - Mandala: Copy random files")

    def init_menubar(self) -> None:
        """Initialize the menu bar."""
        menubar = self.menuBar()
        menubar.setObjectName("MainMenuBar")
        filemenu = menubar.addMenu("File")

        save_config_action = filemenu.addAction("Save Profile")
        save_config_action.setShortcut("Ctrl+S")
        save_config_action.setStatusTip("Save the current GUI profile")
        save_config_action.triggered.connect(self.save_profile)

        save_config_as_action = filemenu.addAction("Save Profile As")
        save_config_as_action.setShortcut("Ctrl+Shift+S")
        save_config_as_action.setStatusTip("Save the current GUI profile as...")
        save_config_as_action.triggered.connect(self.save_profile_as_dialog)

        load_config_action = filemenu.addAction("Load Profile")
        load_config_action.setShortcut("Ctrl+O")
        load_config_action.setStatusTip("Load a GUI profile")
        load_config_action.triggered.connect(self.open_profile_dialog)

    def init_toolbar(self) -> None:
        """Initialize the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setObjectName("MainToolbar")
        self.addToolBar(toolbar)

    def init_statusbar(self) -> None:
        """Initialize the status bar."""
        statusbar = QStatusBar(self, sizeGripEnabled=True)
        statusbar.setObjectName("MainStatusBar")
        self.setStatusBar(statusbar)

    def init_settings(self) -> None:
        """Initialize GUI settings manager."""
        self.restoreGeometry(self.qsettings.value("geometry"))
        self.restoreState(self.qsettings.value("state"))
        self.current_profile = str(self.qsettings.value("profile", ""))
        self.profiles.open_profile(self, self.current_profile)

    @Slot()
    def save_profile(self) -> None:
        """Save the current GUI profile."""
        self.profiles.save_profile(self, self.current_profile)

    @Slot()
    def save_profile_as_dialog(self) -> None:
        """Save a GUI profile via dialog."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Profile As", str(self.profiles.profile_dir), "JSON Files (*.json)"
        )
        if filename:
            self.current_profile = filename
            self.save_profile()
            self.setWindowTitle(f"{Path(self.current_profile).stem} - Mandala: Copy random files")

    @Slot()
    def open_profile_dialog(self) -> None:
        """Load a GUI profile via dialog."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Profile", str(self.profiles.profile_dir), "JSON Files (*.json)"
        )
        if filename:
            self.current_profile = filename
            self.profiles.open_profile(self, filename)
            self.setWindowTitle(f"{Path(self.current_profile).stem} - Mandala: Copy random files")

    def save_settings(self) -> None:
        """Save GUI settings on close."""
        self.qsettings.setValue("geometry", self.saveGeometry())
        self.qsettings.setValue("state", self.saveState())
        self.qsettings.setValue("profile", self.current_profile)
        self.save_profile()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Handle window close event."""
        self.save_settings()
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
    ui_keywords: DualListFilterWidget = field(init=False)
    ui_extensions: DualListFilterWidget = field(init=False)
    ui_filesize: FilesizeFilterWidget = field(init=False)
    ui_duration: DurationFilterWidget = field(init=False)
    ui_weight: DiversityFilterWidget = field(init=False)
    ui_progress: ProgressWidget = field(init=False)
    ui_sect_exec: ExecutionWidget = field(init=False)

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
        self.ui_filesize = FilesizeFilterWidget("Size", "filesize", suffix_options=[s.value for s in SizeUnitEnum])
        self.ui_duration = DurationFilterWidget("Duration", "duration", suffix_options=[s.value for s in TimeUnitEnum])
        self.ui_weight = DiversityFilterWidget("Diversity", "diversity")

        # Init execution components
        self.ui_progress = ProgressWidget()
        self.ui_sect_exec = ExecutionWidget()
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
        layout.addWidget(self.ui_progress, 7, 0, 1, 6)
        layout.addWidget(self.ui_sect_exec, 8, 0, 1, 6)

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
            execution=self.ui_sect_exec.get_config(),
        )
        return MandalaConfig(**model.__dict__)

    @Slot(bool)
    def _toggle_ui(self, *, enabled: bool) -> None:
        """Lock or unlock UI elements."""
        self.ui_sect_exec.btn_stop.setEnabled(not enabled)
        for child in self.findChildren(QWidget):
            if child not in (
                self.ui_sect_exec,
                self.ui_sect_exec.btn_stop,
                self.ui_sect_exec.textbrowser_log,
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
            self.ui_sect_exec.textbrowser_log.append("Error: Invalid configuration")
            return

        self._toggle_ui(enabled=False)

        stall_limit = config.progress.stall_time_limit
        stall_max = int(stall_limit * 100)

        self.ui_progress.progbar_total.setValue(0)
        self.ui_progress.progbar_folder.setValue(0)
        self.ui_progress.progbar_stall.setRange(0, stall_max)
        self.ui_progress.progbar_stall.setValue(stall_max)

        self.worker = RunMandalaWorker(config=config)
        self.worker.signals.progress_total.connect(self.ui_progress.progbar_total.setMaximum)
        self.worker.signals.count_total.connect(self.ui_progress.update_total_prog)

        self.worker.signals.progress.connect(self.ui_progress.progbar_folder.setMaximum)
        self.worker.signals.log.connect(self.ui_sect_exec.textbrowser_log.append)
        self.worker.signals.count.connect(self.ui_progress.progbar_folder.setValue)
        self.worker.signals.time.connect(self.ui_progress.reset_stall_prog)
        self.worker.signals.finished.connect(self._on_finished)

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
