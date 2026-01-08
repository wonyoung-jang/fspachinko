"""Main module for Mandala."""

from __future__ import annotations

import inspect
import os
import random
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, TextIO

import send2trash
import soundfile
from mutagen.mp3 import MP3
from PySide6.QtCore import QDir, QPoint, QSettings, QSize, Qt, QThreadPool, QTimer, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config.constants import (
    BYTES_IN_GIGABYTE,
    BYTES_IN_KILOBYTE,
    BYTES_IN_MEGABYTE,
    SECONDS_IN_MINUTE,
)
from ..gui.components import DblRangeFilterWidget, DualListWidget, RangeFilterWidget
from ..gui.workers import RunMandalaWorker, WorkerSignals
from ..utilities.utils import convert_byte_to_size, convert_string_to_list, strtobool
from .qt_helpers import create_spinbox

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent


@dataclass(slots=True)
class MandalaConfig:
    """Dataclass for Mandala configuration."""

    root: Path = field(default_factory=Path)
    root_absolute: Path = field(default_factory=Path)
    dest: Path = field(default_factory=Path)

    num_files: int = 0

    # Filter Keywords and Extensions
    keywords: list[str] = field(default_factory=list)
    not_keywords: list[str] = field(default_factory=list)
    extensions: list[str] = field(default_factory=list)
    not_extensions: list[str] = field(default_factory=list)

    # Filter Size
    limit_size: bool = False
    min_size: float = 0.0
    max_size: float = 0.0

    # Filter Duration
    limit_duration: bool = False
    min_duration: float = 0.0
    max_duration: float = 0.0

    # Filter Weight
    weight_top: int = 0
    weight_bottom: int = 0

    # Folder Creation
    create_folders: bool = False
    folder_name: str = ""
    unique_folders: bool = True
    num_folders: int = 1

    # Renaming
    index_files: bool = False
    rename_files: bool = False
    rename_name: str = ""

    # Trash
    trash_empty_folders: bool = False
    trash_source_files: bool = False
    trash_invalid_files: bool = False

    def is_extension(self, source: Path) -> bool:
        """Check if a file has the specified extensions."""
        if not self.extensions:
            return True

        for extension in self.extensions:
            if re.compile(rf"\.{extension}$", re.IGNORECASE).search(source.suffix) is not None:
                return True

        return False

    def is_keyword(self, source: Path) -> bool:
        """Check if a file contains the specified keywords."""
        if not self.keywords:
            return True

        for keyword in self.keywords:
            if re.compile(rf"(.*){keyword}(.*)", re.IGNORECASE).search(source.stem) is not None:
                return True

        return False


@dataclass(slots=True)
class MandalaState:
    """Dataclass for Mandala state."""

    touched_files: dict[Path, bool] = field(default_factory=lambda: defaultdict(bool))
    touched_folders: dict[Path, bool] = field(default_factory=lambda: defaultdict(bool))
    path_cache: dict[Path, list[Path]] = field(default_factory=lambda: defaultdict(list))
    weighted_counts: dict[Path, int] = field(default_factory=lambda: defaultdict(int))
    touched_by_weight: dict[Path, bool] = field(default_factory=lambda: defaultdict(bool))
    count: int = 0
    bytes_in_current_folder: int = 0
    start_folder_time: float = 0.0
    start_stall_time: float = 0.0
    is_append_log: bool = False

    def reset_for_folder(self, root_absolute: Path, *, unique_folders: bool) -> None:
        """Reset state variables for a new folder."""
        self.count = 0
        self.bytes_in_current_folder = 0
        self.start_folder_time = perf_counter()
        self.start_stall_time = perf_counter()
        self.weighted_counts.clear()
        self.touched_by_weight.clear()

        if unique_folders:
            self.touched_folders[root_absolute] = False
            for key in self.touched_by_weight:
                self.touched_files[key] = False
                self.touched_folders[key] = False
        else:
            self.touched_files.clear()
            self.touched_folders.clear()
            self.path_cache.clear()


@dataclass(slots=True)
class MandalaMainGui(QWidget):
    """Main application window for Mandala."""

    def __post_init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.was_enabled_map = {}

        self.threadpool = QThreadPool()
        self.worker = RunMandalaWorker(self)
        self.worker.setAutoDelete(False)

        self.state = MandalaState()

        self.log_file: TextIO = None
        self.temp_log_file: TextIO = None

        self.setup_gui()
        self.config = self.get_configuration()
        self.setup_gui_signals()

        self.settings = QSettings()
        self.restore_global_settings()
        self.restore_gui(self.settings)

    def setup_gui_signals(self) -> None:
        """Set up signals for the worker thread."""
        self.signals = WorkerSignals()
        self.signals.count_signal.connect(lambda: self.main_progbar.setValue(self.state.count))
        self.signals.time_signal.connect(self.reset_stall_timer_display)
        self.signals.log_signal.connect(lambda s: self.log_block.append(s))
        self.signals.finished_signal.connect(lambda: self.timer.stop())

    ######################################
    ################# UI #################
    ######################################

    # SETUP SECTION

    def init_file_count_section(self) -> None:
        """Initialize the file count UI components."""
        self.num_file_count = create_spinbox(1, 1_000_000_000, enabled=True)
        self.set_file_count_groupbox = QGroupBox(title="Set Number", flat=True, checkable=True)
        self.set_file_count_groupbox.toggled.connect(self.change_file_label_count)
        count_layout = QHBoxLayout(self.set_file_count_groupbox)
        count_layout.addWidget(QLabel("Count"))
        count_layout.addWidget(self.num_file_count)
        self.min_num_files = create_spinbox(1, 1_000_000_000, enabled=False)
        self.min_num_files.editingFinished.connect(self.switch_file_count)
        self.max_num_files = create_spinbox(2, 1_000_000_000, enabled=False)
        self.max_num_files.editingFinished.connect(self.switch_file_count)
        self.random_file_count_groupbox = QGroupBox(title="Randomize", flat=True, checkable=True, checked=False)
        self.random_file_count_groupbox.toggled.connect(self.switch_file_count)
        self.random_file_count_groupbox.toggled.connect(self.change_file_label_rand)
        random_layout = QGridLayout(self.random_file_count_groupbox)
        random_layout.addWidget(QLabel("Min"), 0, 0)
        random_layout.addWidget(self.min_num_files, 0, 1)
        random_layout.addWidget(QLabel("Max"), 1, 0)
        random_layout.addWidget(self.max_num_files, 1, 1)
        self.file_count_groupbox = QGroupBox(title="File count", flat=True)
        file_count_layout = QHBoxLayout(self.file_count_groupbox)
        file_count_layout.addWidget(self.set_file_count_groupbox)
        file_count_layout.addWidget(self.random_file_count_groupbox)

    def init_root_and_dest_section(self) -> None:
        """Initialize the root and destination UI components."""
        self.root_combobox = QComboBox()
        self.root_combobox.addItem(QDir.rootPath())
        browse_root_btn = QPushButton("Browse")
        browse_root_btn.clicked.connect(self.browse_root)
        delete_root_btn = QPushButton("Delete")
        delete_root_btn.clicked.connect(self.delete_root_item)
        self.root_groupbox = QGroupBox(title="Root", flat=True)
        root_layout = QHBoxLayout(self.root_groupbox)
        root_layout.addWidget(self.root_combobox)
        root_layout.addWidget(browse_root_btn)
        root_layout.addWidget(delete_root_btn)

        self.dest_combobox = QComboBox()
        self.dest_combobox.addItem(QDir.homePath())
        browse_dest_btn = QPushButton("Browse")
        browse_dest_btn.clicked.connect(self.browse_dest)
        delete_dest_btn = QPushButton("Delete")
        delete_dest_btn.clicked.connect(self.delete_dest_item)
        self.dest_groupbox = QGroupBox(title="Destination", flat=True)
        destination_layout = QHBoxLayout(self.dest_groupbox)
        destination_layout.addWidget(self.dest_combobox)
        destination_layout.addWidget(browse_dest_btn)
        destination_layout.addWidget(delete_dest_btn)

    def setup_setup_section(self) -> None:
        """Set up the setup tab UI components."""
        self.init_file_count_section()
        self.init_root_and_dest_section()

        self.num_folders_count_spinbox = create_spinbox(1, 100000, enabled=True)
        self.name_of_folders_entry_lineedit = QLineEdit("Folder Name")
        self.is_make_folders_unique_checkbox = QCheckBox("Make Unique")
        self.is_make_folders_unique_checkbox.setChecked(True)
        self.folders_groupbox = QGroupBox(title="Create Folders", flat=True, checkable=True)
        create_folders_layout = QGridLayout(self.folders_groupbox)
        create_folders_layout.addWidget(QLabel("Count"), 0, 0)
        create_folders_layout.addWidget(self.num_folders_count_spinbox, 0, 1)
        create_folders_layout.addWidget(QLabel("Name"), 1, 0)
        create_folders_layout.addWidget(self.name_of_folders_entry_lineedit, 1, 1)
        create_folders_layout.addWidget(self.is_make_folders_unique_checkbox, 2, 0, 1, 2)

        keep_filename = QRadioButton("Keep")
        keep_filename.setChecked(True)
        self.index_filename_radio = QRadioButton("Index")
        self.rename_filename_radio = QRadioButton("Rename")
        self.rename_filename_radio.toggled.connect(
            lambda: self.rename_filename_entry.setEnabled(self.rename_filename_radio.isChecked())
        )
        self.rename_filename_entry = QLineEdit("New Name")
        self.rename_filename_entry.setEnabled(False)
        self.filename_groupbox = QGroupBox(title="Filenames", flat=True, checkable=True)
        filename_layout = QGridLayout(self.filename_groupbox)
        filename_layout.addWidget(keep_filename, 0, 0, 1, 2)
        filename_layout.addWidget(self.index_filename_radio, 1, 0, 1, 2)
        filename_layout.addWidget(self.rename_filename_radio, 2, 0)
        filename_layout.addWidget(self.rename_filename_entry, 2, 1)

        self.is_trash_empty = QCheckBox("Empty Folders")
        self.is_trash_source = QCheckBox("Valid Files")
        self.is_trash_invalid = QCheckBox("Invalid Files")
        self.trash_groupbox = QGroupBox(title="Trash", flat=True, checkable=True)
        trash_layout = QVBoxLayout(self.trash_groupbox)
        trash_layout.addWidget(self.is_trash_empty)
        trash_layout.addWidget(self.is_trash_source)
        trash_layout.addWidget(self.is_trash_invalid)

        self.setup_section = QWidget()
        layout = QGridLayout(self.setup_section)
        layout.addWidget(self.file_count_groupbox, 0, 0, 1, 6)
        layout.addWidget(self.root_groupbox, 1, 0, 1, 3)
        layout.addWidget(self.dest_groupbox, 1, 3, 1, 3)
        layout.addWidget(self.folders_groupbox, 2, 0, 1, 2)
        layout.addWidget(self.filename_groupbox, 2, 2, 1, 2)
        layout.addWidget(self.trash_groupbox, 2, 4, 1, 2)

    # FILTER SECTION

    def setup_filter_section(self) -> None:
        """Set up the customize tab UI components."""
        self.filter_keywords = DualListWidget(title="Keywords", parent=self)
        self.filter_extensions = DualListWidget(title="Extensions", parent=self)
        self.filter_filesize = DblRangeFilterWidget(title="Size", suffix_options=("B", "KB", "MB", "GB"), parent=self)
        self.filter_duration = DblRangeFilterWidget(title="Duration", suffix_options=("s", "m"), parent=self)
        self.filter_weight = RangeFilterWidget(title="Weight", parent=self)

        self.filter_section = QWidget()
        layout = QGridLayout(self.filter_section)
        layout.addWidget(self.filter_keywords, 0, 0, 1, 3)
        layout.addWidget(self.filter_extensions, 1, 0, 1, 3)
        layout.addWidget(self.filter_filesize, 2, 0)
        layout.addWidget(self.filter_duration, 2, 1)
        layout.addWidget(self.filter_weight, 2, 2)

    # SIDEBAR SECTION

    def setup_sidebar_section(self) -> None:
        """Set up the sidebar UI components."""
        self.log_invalid_checkbox = QCheckBox("Log Invalid")
        self.log_invalid_checkbox.setChecked(True)

        open_root_btn = QPushButton("Root")
        open_root_btn.clicked.connect(lambda: os.startfile(self.config.root))

        open_dest_btn = QPushButton("Destination")
        open_dest_btn.clicked.connect(lambda: os.startfile(self.config.dest))

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_config)

        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self.load_config)

        default_btn = QPushButton("Set Default")
        default_btn.clicked.connect(lambda: self.save_gui(self.settings))

        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(lambda: self.restore_gui(self.settings))

        self.sidebar_section = QWidget()
        layout = QVBoxLayout(self.sidebar_section)
        layout.addWidget(load_btn)
        layout.addWidget(save_btn)
        layout.addWidget(open_root_btn)
        layout.addWidget(open_dest_btn)
        layout.addWidget(default_btn)
        layout.addWidget(reset_btn)
        layout.addStretch()
        layout.addWidget(self.log_invalid_checkbox)

    # RUN SECTION

    def setup_run_section(self) -> None:
        """Set up the run section UI components."""
        # PROGRESS BAR
        self.main_progbar = QProgressBar(value=0, format="%v", textVisible=True, alignment=Qt.AlignmentFlag.AlignCenter)

        # RUN BUTTON
        self.run_btn = QPushButton("Start")
        self.run_btn.clicked.connect(self.run_mandala_push)

        # STOP BUTTON
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self.stop_mandala_push)

        self.stop_tracker = False

        # STALL TIMER BAR DISPLAY
        self.stall_time_dblspin = QDoubleSpinBox(suffix=" s", decimals=1, minimum=1.0, maximum=600_000.0, value=10.0)
        self.stall_time_dblspin.valueChanged.connect(self.change_stall_time_spinbox)

        self.stall_time_limit = self.stall_time_dblspin.value()

        self.stall_time_progbar = QProgressBar(textVisible=False)
        self.stall_time_progbar.setMaximumHeight(8)

        self.stall_time_counter_label = QLabel(f"{self.stall_time_limit}0 s")
        self.stall_time_counter_label.setVisible(False)

        self.log_block = QTextBrowser()
        self.log_block.setMinimumHeight(150)
        self.log_block.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        self.timer = QTimer(singleShot=False, timerType=Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.update_timer)

        self.run_section = QWidget()
        layout = QGridLayout(self.run_section)
        layout.addWidget(self.log_block, 0, 0, 1, 3)
        layout.addWidget(self.stall_time_progbar, 1, 0)
        layout.addWidget(self.stall_time_dblspin, 1, 1)
        layout.addWidget(self.stall_time_counter_label, 1, 2)
        layout.addWidget(self.main_progbar, 2, 0)
        layout.addWidget(self.run_btn, 2, 1)
        layout.addWidget(self.stop_btn, 2, 2)

    # SETUP UI

    def setup_gui(self) -> None:
        """Set up the main UI components."""
        self.setup_setup_section()
        self.setup_filter_section()
        self.setup_sidebar_section()
        self.setup_run_section()

        self.setWindowTitle("Mandala: Copy random files")

        layout = QGridLayout(self)
        layout.addWidget(self.setup_section, 0, 0)
        layout.addWidget(self.filter_section, 1, 0)
        layout.addWidget(self.sidebar_section, 0, 1, 2, 1)
        layout.addWidget(self.run_section, 2, 0, 1, 2)

    ###########################################
    ################# METHODS #################
    ###########################################

    ### ROOT AND DESTINATION METHODS ###

    def reset_path_to_start(self) -> Path:
        """Reset the current working directory to the start root path."""
        os.chdir(self.config.root)
        return Path.cwd()

    ### RUN METHODS ###

    def get_configuration(self) -> MandalaConfig:
        """Get the current configuration as a MandalaConfig dataclass."""
        # File Size Variables
        size_unit = self.filter_filesize.combo.currentText()
        min_size = self.filter_filesize.min_spin.value()
        max_size = self.filter_filesize.max_spin.value()
        if size_unit == "KB":
            min_size *= BYTES_IN_KILOBYTE
            max_size *= BYTES_IN_KILOBYTE
        elif size_unit == "MB":
            min_size *= BYTES_IN_MEGABYTE
            max_size *= BYTES_IN_MEGABYTE
        elif size_unit == "GB":
            min_size *= BYTES_IN_GIGABYTE
            max_size *= BYTES_IN_GIGABYTE

        # File Duration Variables
        min_duration = self.filter_duration.min_spin.value()
        max_duration = self.filter_duration.max_spin.value()
        if self.filter_duration.combo.currentText() == "m":
            min_duration *= SECONDS_IN_MINUTE
            max_duration *= SECONDS_IN_MINUTE

        root_path = Path(self.root_combobox.currentText())
        return MandalaConfig(
            root=root_path,
            root_absolute=root_path.resolve(),
            dest=Path(self.dest_combobox.currentText()),
            num_files=self.num_file_count.value(),
            keywords=(
                convert_string_to_list(self.filter_keywords.include_edit.text())
                if self.filter_keywords.include_groupbox.isChecked()
                else []
            ),
            not_keywords=(
                convert_string_to_list(self.filter_keywords.exclude_edit.text())
                if self.filter_keywords.exclude_groupbox.isChecked()
                else []
            ),
            extensions=(
                convert_string_to_list(self.filter_extensions.include_edit.text())
                if self.filter_extensions.include_groupbox.isChecked()
                else []
            ),
            not_extensions=(
                convert_string_to_list(self.filter_extensions.exclude_edit.text())
                if self.filter_extensions.exclude_groupbox.isChecked()
                else []
            ),
            limit_size=self.filter_filesize.isChecked(),
            min_size=round(min_size, 2),
            max_size=round(max_size, 2),
            limit_duration=self.filter_duration.isChecked(),
            min_duration=min_duration,
            max_duration=max_duration,
            weight_top=self.filter_weight.min_spin.value(),
            weight_bottom=self.filter_weight.max_spin.value(),
            create_folders=self.folders_groupbox.isChecked(),
            folder_name=self.name_of_folders_entry_lineedit.text(),
            unique_folders=self.is_make_folders_unique_checkbox.isChecked(),
            num_folders=self.num_folders_count_spinbox.value() if self.folders_groupbox.isChecked() else 1,
            index_files=self.index_filename_radio.isChecked() if self.filename_groupbox.isChecked() else False,
            rename_files=self.rename_filename_radio.isChecked() if self.filename_groupbox.isChecked() else False,
            rename_name=self.rename_filename_entry.text() if self.filename_groupbox.isChecked() else "",
            trash_empty_folders=self.is_trash_empty.isChecked() if self.trash_groupbox.isChecked() else False,
            trash_source_files=self.is_trash_source.isChecked() if self.trash_groupbox.isChecked() else False,
            trash_invalid_files=self.is_trash_invalid.isChecked() if self.trash_groupbox.isChecked() else False,
        )

    def run_mandala(self) -> None:
        """Run the main file copying process."""
        for _ in range(self.config.num_folders):
            if self.stop_tracker:
                break

            self.process_folder()

        self.stop_mandala()

    def get_file_count_for_run(self) -> int:
        """Get the number of files to process for the current run."""
        if self.random_file_count_groupbox.isChecked():
            return random.randint(self.min_num_files.value(), self.max_num_files.value())
        return self.config.num_files

    def process_folder(self) -> None:
        """Process a single folder for file copying."""
        root_absolute = self.config.root_absolute

        self.state.reset_for_folder(root_absolute, unique_folders=self.config.unique_folders)

        top_weight_mark = Path()
        curr_dest = self.create_folders(self.config.dest)

        temp_log_file = Path(self.log_file.name + ".tmp")
        self.temp_log_file = temp_log_file.open("a", encoding="utf-8")

        main_path = self.reset_path_to_start()

        # File Count
        num_files = self.get_file_count_for_run()
        self.main_progbar.setRange(0, num_files)

        for curr_file in range(num_files):
            if self.stop_tracker:
                break

            if self.state.touched_folders[root_absolute] and self.is_timed_out():
                break

            main_path = self.process_file(main_path, top_weight_mark, curr_file, curr_dest)

        #########################  END OF FOLDER  #########################
        self.end_folder_actions(curr_dest)

    def process_file(self, main_path: Path, top_mark: Path, curr_file: int, curr_dest: Path) -> Path:
        """Process a single file for copying."""
        while not self.state.touched_folders[self.config.root_absolute] and not self.is_timed_out():
            if self.stop_tracker:
                return main_path

            main_path_absolute = main_path.resolve()
            # Try to get main path
            try:
                if not self.state.path_cache.setdefault(main_path_absolute, []):
                    self.state.path_cache[main_path_absolute] = list(main_path.iterdir())
            except PermissionError:
                self.state.touched_folders[main_path_absolute] = True
                main_path = self.reset_path_to_start()
                continue

            # If folder is empty
            if len(self.state.path_cache[main_path_absolute]) == 0:
                self.state.touched_folders[main_path_absolute] = True
                if self.config.trash_empty_folders:
                    send2trash.send2trash(str(main_path_absolute))
                main_path = self.reset_path_to_start()
            # If the folder is not empty
            else:
                # Chooses random path and stores absolute path
                random_path = Path(random.choice(self.state.path_cache[main_path_absolute]))
                random_path_absolute = random_path.resolve()
                # If touched, try again:
                if self.state.touched_files[random_path_absolute] or self.state.touched_folders[random_path_absolute]:
                    self.touch_folder_if_all_files_touched(
                        self.state.path_cache[main_path_absolute], main_path_absolute
                    )
                    main_path = self.reset_path_to_start()
                elif random_path.is_dir():
                    main_path, top_mark = self.handle_random_path_is_dir(
                        random_path, random_path_absolute, main_path, top_mark
                    )
                elif random_path.is_file():
                    # Touch the file and get size
                    self.state.touched_files[random_path_absolute] = True
                    random_path_size = Path(random_path).stat().st_size
                    random_path_relative = Path(os.path.relpath(random_path, self.config.root))
                    # If file is valid
                    if self.is_valid_file(random_path, random_path_size) and self.copy_files_to_target(
                        curr_file, random_path, curr_dest, random_path_size
                    ):
                        self.handle_log(random_path_relative, curr_file)
                        self.state.bytes_in_current_folder += random_path_size
                        self.state.count += 1
                        self.signals.count_signal.emit()
                        self.state.start_stall_time = perf_counter()
                        self.signals.time_signal.emit()
                        if self.config.trash_source_files:
                            send2trash.send2trash(str(random_path_absolute))

                        self.handle_weights(top_mark, main_path_absolute)
                        main_path = self.reset_path_to_start()
                        break

                    # If file is invalid
                    self.handle_invalid_file(random_path_relative, random_path_absolute)
                    main_path = self.reset_path_to_start()
        return main_path

    def handle_log(self, random_path: Path, curr_file: int) -> None:
        """Handle logging of valid files."""
        msg = f"{curr_file + 1}: {random_path}"
        if self.state.is_append_log:
            self.temp_log_file.write(f"{msg}\n")
        else:
            self.log_file.write(f"{msg}\n")
        self.signals.log_signal.emit(msg)

    def handle_invalid_file(self, random_path: Path, random_path_absolute: Path) -> None:
        """Handle invalid files by logging and trashing if necessary."""
        count = self.state.count
        if self.log_invalid_checkbox.isChecked():
            prefix = "**"
            if count >= 100:
                prefix = "***"
            elif count >= 1000:
                prefix = "****"
            self.signals.log_signal.emit(f"{prefix}: {random_path}")
        if self.config.trash_invalid_files:
            send2trash.send2trash(random_path_absolute)

    def handle_weights(self, top_mark: Path, bottom_mark: Path) -> None:
        """Handle weight assignments for folders."""
        weight_top = self.config.weight_top
        weight_bottom = self.config.weight_bottom
        weighted_counts = self.state.weighted_counts
        touched_folders = self.state.touched_folders
        touched_by_weight = self.state.touched_by_weight

        if weight_top > 0:
            weighted_counts[top_mark] += 1
            if weighted_counts[top_mark] == weight_top:
                touched_folders[top_mark] = True
                touched_by_weight[top_mark] = True

        if weight_bottom > 0:
            weighted_counts[bottom_mark] += 1
            if weighted_counts[bottom_mark] == weight_bottom:
                touched_folders[bottom_mark] = True
                touched_by_weight[bottom_mark] = True

    def handle_random_path_is_dir(
        self, random_path: Path, random_path_absolute: Path, main_path: Path, top_weight_mark: Path
    ) -> tuple[Path, Path]:
        """Handle the case when the random path is a directory."""
        try:
            os.chdir(random_path)
            main_path = Path.cwd()
            if self.config.weight_top > 0 and Path(random_path_absolute).parent == self.config.root:
                top_weight_mark = random_path_absolute
        except PermissionError:
            self.state.touched_folders[random_path_absolute] = True
            main_path = self.reset_path_to_start()
        return main_path, top_weight_mark

    def end_folder_actions(self, curr_dest: Path) -> None:
        """Create and write log at the end of folder."""
        self.temp_log_file.close()
        self.log_file.close()
        self.signals.log_signal.emit(self.write_status_log(curr_dest))

        # Terminates the program if no files were collected
        if self.state.count == 0:
            create_folders = self.config.create_folders
            if create_folders:
                shutil.rmtree(curr_dest)
            elif not (create_folders or self.state.is_append_log):
                Path(self.log_file.name).unlink()

    def is_valid_file(self, source: Path, size: int) -> bool:
        """Check if a file is valid based on the current filters."""
        # If no limit, all valid, else checks valid size range. Returns immediately if neither
        if not self.config.limit_size or self.config.min_size > size > self.config.max_size:
            return False

        # If a blacklist extension or keyword is found, immediately return invalid
        for not_extension in self.config.not_extensions:
            if re.compile(rf"\.{not_extension}$", re.IGNORECASE).search(source.suffix) is not None:
                return False

        for not_keyword in self.config.not_keywords:
            if re.compile(rf"(.*){not_keyword}(.*)", re.IGNORECASE).search(source.stem) is not None:
                return False

        # If no extension or keyword, all valid.
        # If whitelist item found, immediately breaks
        is_extension = self.is_extension(source)
        is_keyword = self.is_keyword(source)

        # If a duration can be get it will be checked, otherwise skips
        is_within_duration = self.is_within_duration(source)

        # Checks that everything is True
        return is_extension and is_keyword and is_within_duration

    def is_extension(self, source: Path) -> bool:
        """Check if a file has the specified extensions."""
        if not self.config.extensions:
            return True

        for extension in self.config.extensions:
            if re.compile(rf"\.{extension}$", re.IGNORECASE).search(source.suffix) is not None:
                return True

        return False

    def is_keyword(self, source: Path) -> bool:
        """Check if a file contains the specified keywords."""
        if not self.config.keywords:
            return True

        for keyword in self.config.keywords:
            if re.compile(rf"(.*){keyword}(.*)", re.IGNORECASE).search(source.stem) is not None:
                return True

        return False

    def is_within_duration(self, source: Path) -> bool:
        """Check if a file is within the specified duration range."""
        if not self.config.limit_duration:
            return True

        mp3_suffix = ".mp3"
        duration = 0.0
        min_duration = self.config.min_duration
        max_duration = self.config.max_duration

        try:
            sound = soundfile.SoundFile(source)
            duration = len(sound) / sound.samplerate
        except RuntimeError:
            try:
                if source.suffix == mp3_suffix:
                    duration = MP3(source).info.length
                    return min_duration <= duration <= max_duration
            except ValueError:
                return True
            else:
                return True
        except ValueError:
            return True

        return min_duration <= duration <= max_duration

    def copy_files_to_target(self, file_num: int, source: Path, dest: Path, source_size: int) -> bool | None:
        """Copy files to the target destination with appropriate naming."""
        source_absolute = source.resolve()
        source_name = source.name
        try:
            if self.config.index_files:
                shutil.copy(source_absolute, dest / f"{file_num + 1}.{source_name}")
            elif self.config.rename_files:
                rename_name = self.config.rename_name
                if not (dest / f"{rename_name} {file_num + 1}{source.suffix}").exists():
                    shutil.copy(source_absolute, dest / f"{rename_name} {file_num + 1}{source.suffix}")
                else:
                    x = 1
                    while (dest / f"{rename_name} {file_num + x}{source.suffix}").exists():
                        x += 1
                    shutil.copy(source_absolute, dest / f"{rename_name} {file_num + x}{source.suffix}")
            else:
                x = 2
                while (dest / f"{source_name}").exists():
                    if source_size == (dest / f"{source_name}").stat().st_size:
                        return False
                    source_name = source.stem + f" ({x})" + source.suffix
                    x += 1
                shutil.copy(source_absolute, dest / f"{source_name}")
        except PermissionError:
            return False

        return True

    def create_folders(self, dest: Path) -> Path:
        """Create folders in the destination if specified."""
        final_dest = dest
        log_path = Path(final_dest / f"!{final_dest.name}_log.txt")

        if not self.config.create_folders:
            self.state.is_append_log = log_path.exists()
            self.log_file = log_path.open("a", encoding="utf-8")
        else:
            folder_name = self.config.folder_name
            try:
                Path(f"{final_dest}/{folder_name}").mkdir()
                final_dest = final_dest / f"{folder_name}"
                self.log_file = (final_dest / f"!{folder_name}_log.txt").open("a", encoding="utf-8")
            except FileExistsError:
                for x in range(len(list(final_dest.iterdir()))):
                    try:
                        Path(f"{final_dest}/{folder_name} {x + 2}").mkdir()
                        final_dest = final_dest / f"{folder_name} {x + 2}"
                        self.log_file = (final_dest / f"!{folder_name} {x + 2}_log.txt").open("a", encoding="utf-8")
                        break
                    except FileExistsError:
                        continue
        return final_dest

    def touch_folder_if_all_files_touched(self, list_of_paths: list[Path], absolute_path: Path) -> None:
        """Mark folder as touched if all files inside are touched."""
        for file_folder in list_of_paths:
            path = file_folder.resolve()
            if self.state.touched_files[path] or self.state.touched_folders[path]:
                pass
            else:
                return
        self.state.touched_folders[absolute_path] = True

    ### PROGRESS & TIMER METHODS ###

    def is_timed_out(self) -> bool:
        """Check if the process has timed out based on stall time."""
        return (perf_counter() - self.state.start_stall_time) > self.stall_time_limit

    def stop_mandala(self) -> None:
        """Stop mandala process and reset UI elements."""
        self.signals.finished_signal.emit()

        self.temp_log_file.close()
        self.log_file.close()

        self.run_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.stall_time_counter_label.setVisible(False)
        self.stall_time_dblspin.setVisible(True)
        self.stall_time_counter_label.setText(f"{self.stall_time_limit}0 s")

        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QWidget) and name not in ("stop_btn", "log_block"):
                obj.setEnabled(self.was_enabled_map[name])

    ### LOG METHODS ###

    def write_status_log(self, curr_dest: Path) -> str:
        """Write the status log at the end of each folder."""
        runtime = round(perf_counter() - self.state.start_folder_time, 2)
        timed_out = self.is_timed_out()
        all_searched = self.state.touched_folders[self.config.root_absolute]
        num_files = self.config.num_files

        count = self.state.count
        create_folders = self.config.create_folders

        if count == num_files:
            status = f"SUCCESS: {count}/{num_files} files copied"
        elif self.stop_tracker:
            status = f"STOPPED: {count}/{num_files} files copied"
        elif count == 0 and create_folders and (timed_out or all_searched):
            reason = "timed out" if timed_out else "all files searched"
            status = f"NO FILES FOUND: {reason} | folder deleted"
        elif all_searched:
            status = f"ALL FILES SEARCHED: {count}/{num_files} files copied"
        elif timed_out:
            status = f"TIMED OUT: {count}/{num_files} files copied"
        else:
            status = "FINISHED"

        _extensions = self.config.extensions
        _keywords = self.config.keywords
        ext_str = ", ".join([f".{e}" for e in _extensions]) if _extensions else "All"
        kw_str = ", ".join([f'"{k}"' for k in _keywords]) if _keywords else "All"

        report = (
            "------------------------------------------------------------------------\n"
            f"{status}\n"
            "------------------------------------------------------------------------\n"
            f"Date:             {datetime.now(tz=UTC).strftime('%B %d, %Y')}\n"
            f"Time:             {datetime.now(tz=UTC).strftime('%I:%M:%S%p')}\n"
            f"Start:            {self.config.root}\n"
            f"Destination:      {curr_dest}\n"
            f"Extensions:       {ext_str}\n"
            f"Keywords:         {kw_str}\n"
            f"Total size:       {convert_byte_to_size(self.state.bytes_in_current_folder)}\n"
            f"Total runtime:    {runtime}s\n"
            "------------------------------------------------------------------------"
        )
        self.prepend_status_to_log(report)
        return report

    def prepend_status_to_log(self, status: str) -> None:
        """Prepend the status to the log file."""
        log_path = Path(self.log_file.name)
        temp_log_path = Path(self.temp_log_file.name)

        if self.state.is_append_log:
            with temp_log_path.open(encoding="utf-8") as content, log_path.open("a", encoding="utf-8") as out:
                out.write(status + "\n")
                shutil.copyfileobj(content, out)
            temp_log_path.unlink()
        else:
            with log_path.open(encoding="utf-8") as existing, temp_log_path.open("w", encoding="utf-8") as out:
                out.write(status + "\n")
                shutil.copyfileobj(existing, out)
            log_path.unlink()
            temp_log_path.rename(self.log_file.name)

    ### SETTINGS METHODS ###

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Close event to save settings."""
        self.save_global_settings()
        super().closeEvent(event)

    def save_global_settings(self) -> None:
        """Save GUI settings to registry."""
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
        self.settings.setValue("show_invalid", self.log_invalid_checkbox.isChecked())

    def restore_global_settings(self) -> None:
        """Restore GUI settings from registry."""
        size = self.settings.value("size", QSize(500, 500))
        if isinstance(size, QSize):
            self.resize(size)

        pos = self.settings.value("pos", QPoint(60, 60))
        if isinstance(pos, QPoint):
            self.move(pos)

        val = self.settings.value("show_invalid")
        if val is not None:
            self.log_invalid_checkbox.setChecked(strtobool(val))

    #############################
    ########### SLOTS ###########
    #############################

    ### ROOT AND DESTINATION SLOTS ###

    @Slot()
    def browse_root(self) -> None:
        """Browse for a new root directory."""
        d = QFileDialog.getExistingDirectory(self, "Select Root Folder")
        if d:
            if self.root_combobox.findText(d) == -1:
                self.root_combobox.addItem(d)
            self.root_combobox.setCurrentIndex(self.root_combobox.findText(d))

    @Slot()
    def browse_dest(self) -> None:
        """Browse for a new destination directory."""
        d = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if d:
            if self.dest_combobox.findText(d) == -1:
                self.dest_combobox.addItem(d)
            self.dest_combobox.setCurrentIndex(self.dest_combobox.findText(d))

    @Slot()
    def delete_root_item(self) -> None:
        """Delete the current root item from the combo box."""
        if self.root_combobox.count() > 1:
            self.root_combobox.removeItem(self.root_combobox.currentIndex())

    @Slot()
    def delete_dest_item(self) -> None:
        """Delete the current destination item from the combo box."""
        if self.dest_combobox.count() > 1:
            self.dest_combobox.removeItem(self.dest_combobox.currentIndex())

    ### PROGRESS & TIMER SLOTS ###

    @Slot()
    def reset_stall_timer_display(self) -> None:
        """Reset the stall time progress bar and counter display."""
        self.stall_time_progbar.setValue(self.stall_time_progbar.maximum())
        self.stall_time_counter_label.setText(f"{self.stall_time_progbar.value() / 100} s")

    @Slot()
    def change_stall_time_spinbox(self) -> None:
        """Change the stall time limit based on the spin box value."""
        self.stall_time_limit = self.stall_time_dblspin.value()
        self.stall_time_counter_label.setText(f"{self.stall_time_limit}0 s")

    @Slot()
    def update_timer(self) -> None:
        """Update the stall time progress bar and counter."""
        self.stall_time_progbar.setValue(self.stall_time_progbar.value() - 1)
        self.stall_time_counter_label.setText(f"{self.stall_time_progbar.value() / 100} s")

    @Slot()
    def run_mandala_push(self) -> None:
        """Start the mandala process and disable UI elements."""
        try:
            self.config = self.get_configuration()
        except ValueError:
            self.log_block.append("Error: Invalid configuration")
            return

        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QWidget) and name not in ("stop_btn", "log_block"):
                self.was_enabled_map[name] = obj.isEnabled()
                obj.setEnabled(False)

        self.main_progbar.reset()
        self.stall_time_progbar.setRange(0, int(self.stall_time_limit * 100))
        self.stall_time_progbar.setValue(self.stall_time_progbar.maximum())
        self.stall_time_counter_label.setText(f"{self.stall_time_limit}0 s")

        self.timer.start(10)
        self.run_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        self.stall_time_counter_label.setVisible(True)
        self.stall_time_dblspin.setVisible(False)
        self.stop_tracker = False

        self.threadpool.globalInstance().start(self.worker)

    @Slot()
    def stop_mandala_push(self) -> None:
        """Stop the mandala process."""
        self.stop_tracker = True

    ### FILE COUNT SLOTS ###

    @Slot()
    def switch_file_count(self) -> None:
        """Switch the file count low and high values."""
        if self.random_file_count_groupbox.isChecked():
            lo, hi = self.min_num_files.value(), self.max_num_files.value()
            if lo > hi:
                self.min_num_files.setValue(hi)
                self.max_num_files.setValue(lo)

    @Slot()
    def change_file_label_rand(self) -> None:
        """Change file count group box based on random or count selection."""
        is_rand = self.random_file_count_groupbox.isChecked()
        self.set_file_count_groupbox.setChecked(not is_rand)
        self._toggle_group_children(self.random_file_count_groupbox, enabled=is_rand)
        self._toggle_group_children(self.set_file_count_groupbox, enabled=not is_rand)

    @Slot()
    def change_file_label_count(self) -> None:
        """Change file count group box based on random or count selection."""
        is_fixed = self.set_file_count_groupbox.isChecked()
        self.random_file_count_groupbox.setChecked(not is_fixed)
        self._toggle_group_children(self.set_file_count_groupbox, enabled=is_fixed)
        self._toggle_group_children(self.random_file_count_groupbox, enabled=not is_fixed)

    def _toggle_group_children(self, groupbox: QGroupBox, *, enabled: bool) -> None:
        """Enable or disable all children of a group box."""
        for child in groupbox.children():
            if isinstance(child, QWidget):
                child.setEnabled(enabled)

    ### SETTINGS SLOTS ###

    @Slot()
    def save_config(self) -> None:
        """Save GUI settings to registry."""
        save_file, _ = QFileDialog.getSaveFileName(self, "Save Config", "config.ini", "Configuration (*.ini)")
        if save_file:
            self.save_gui(QSettings(save_file, QSettings.Format.IniFormat))
            self.setWindowTitle(f"{Path(save_file).stem} - Mandala: Copy random files")

    @Slot()
    def load_config(self) -> None:
        """Load GUI settings from registry."""
        open_file, _ = QFileDialog.getOpenFileName(self, "Load Config", "", "Configuration (*.ini)")
        if open_file:
            self.restore_gui(QSettings(open_file, QSettings.Format.IniFormat))
            self.setWindowTitle(f"{Path(open_file).stem} - Mandala: Copy random files")

    @Slot()
    def save_gui(self, settings: QSettings) -> None:
        """Save GUI settings to registry."""
        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QComboBox):
                settings.setValue(name, [obj.itemText(i) for i in range(obj.count())])
                settings.setValue(f"current{name}", obj.currentText())
            elif isinstance(obj, QLineEdit):
                settings.setValue(name, obj.text())
            elif isinstance(obj, (QSpinBox, QDoubleSpinBox)):
                settings.setValue(name, obj.value())
            elif isinstance(obj, (QCheckBox, QRadioButton)):
                settings.setValue(name, obj.isChecked())

    @Slot()
    def restore_gui(self, settings: QSettings) -> None:
        """Restore GUI settings from registry."""
        for name, obj in inspect.getmembers(self):
            if (val := settings.value(name)) is None:
                continue

            if isinstance(obj, QComboBox):
                obj.addItems(val)
                curr = settings.value(f"current{name}")
                if curr:
                    if obj.findText(curr) == -1:
                        obj.addItem(curr)
                    obj.setCurrentIndex(obj.findText(curr))
            elif isinstance(obj, QLineEdit):
                obj.setText(val)
            elif isinstance(obj, QSpinBox):
                obj.setValue(int(val))
            elif isinstance(obj, QDoubleSpinBox):
                obj.setValue(float(val))
            elif isinstance(obj, (QCheckBox, QRadioButton)):
                obj.setChecked(strtobool(val) if isinstance(val, str) else bool(val))
