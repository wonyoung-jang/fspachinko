"""Main module for Mandala."""

from __future__ import annotations

import inspect
import os
import random
import re
import shutil
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

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
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config.constants import (
    BYTES_IN_GIGABYTE,
    BYTES_IN_KILOBYTE,
    BYTES_IN_MEGABYTE,
    NOWRAP,
    SECONDS_IN_MINUTE,
)
from ..gui.workers import RunMandalaWorker, WorkerSignals
from ..utilities.utils import convert_byte_to_size, convert_string_to_list, strtobool
from .qt_helpers import create_spinbox

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent


class MainWindow(QWidget):
    """Main application window for Mandala."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.wasEnabled = {}
        self.listOfPaths = defaultdict(bool)

        self.threadpool = QThreadPool()
        self.worker = RunMandalaWorker(self)
        self.worker.setAutoDelete(False)

        self.setup_ui()
        self.setup_signals()

        self.settings = QSettings()
        self.restore_global_settings()
        self.restore_gui(self.settings)

    def setup_signals(self) -> None:
        """Set up signals for the worker thread."""
        self.signals = WorkerSignals()
        self.signals.count_signal.connect(lambda: self.progressBar.setValue(self.count))
        self.signals.time_signal.connect(
            lambda: self.stallTimeProgressBar.setValue(self.stallTimeProgressBar.maximum())
        )
        self.signals.time_signal.connect(
            lambda: self.stallTimeCounter.setText(f"{self.stallTimeProgressBar.value() / 100} s")
        )
        self.signals.log_signal.connect(lambda s: self.logBlock.append(s))
        self.signals.finished_signal.connect(lambda: self.timer.stop())

    # SETUP SECTION

    def setup_file_count_ui(self) -> None:
        """Set up the file count UI components."""
        self.num_file_count = create_spinbox(1, 1000000000, enabled=True)

        self.set_file_count_groupbox = QGroupBox(title="Set Number", flat=True, checkable=True)
        self.set_file_count_groupbox.toggled.connect(self.change_file_label_count)
        count_layout = QHBoxLayout(self.set_file_count_groupbox)
        count_layout.addWidget(QLabel("Count"))
        count_layout.addWidget(self.num_file_count)

        self.min_num_files = create_spinbox(1, 1000000000, enabled=False)
        self.min_num_files.editingFinished.connect(self.switch_file_count)

        self.max_num_files = create_spinbox(2, 1000000000, enabled=False)
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
        layout = QHBoxLayout(self.file_count_groupbox)
        layout.addWidget(self.set_file_count_groupbox)
        layout.addWidget(self.random_file_count_groupbox)

    def setup_root_ui(self) -> None:
        """Set up the root UI components."""
        self.root = QDir.rootPath()

        self.root_directory = self.root

        self.root_combobox = QComboBox()
        self.root_combobox.addItem(self.root)
        self.root_combobox.currentTextChanged.connect(self.change_root)

        browse_root_button = QPushButton("Browse")
        browse_root_button.clicked.connect(self.browse_root)

        delete_root_button = QPushButton("Delete")
        delete_root_button.clicked.connect(self.delete_root_item)

        self.root_groupbox = QGroupBox(title="Root", flat=True)
        layout = QHBoxLayout(self.root_groupbox)
        layout.addWidget(self.root_combobox)
        layout.addWidget(browse_root_button)
        layout.addWidget(delete_root_button)

    def setup_dest_ui(self) -> None:
        """Set up the destination UI components."""
        self.dest = QDir.homePath()

        self.dest_directory = self.dest

        self.dest_combobox = QComboBox()
        self.dest_combobox.addItem(self.dest)
        self.dest_combobox.currentTextChanged.connect(self.change_destination)

        browse_dest_button = QPushButton("Browse")
        browse_dest_button.clicked.connect(self.browse_destination)

        delete_dest_button = QPushButton("Delete")
        delete_dest_button.clicked.connect(self.delete_dest_item)

        self.dest_groupbox = QGroupBox(title="Destination", flat=True)
        layout = QHBoxLayout(self.dest_groupbox)
        layout.addWidget(self.dest_combobox)
        layout.addWidget(browse_dest_button)
        layout.addWidget(delete_dest_button)

    def setup_create_folders_ui(self) -> None:
        """Set up the create folders UI components."""
        self.num_folders_count_spinbox = create_spinbox(1, 100000, enabled=True)

        self.name_of_folders_entry_lineedit = QLineEdit("Folder Name")

        self.is_make_folders_unique_checkbox = QCheckBox("Make Unique")
        self.is_make_folders_unique_checkbox.setChecked(True)

        self.folders_groupbox = QGroupBox(title="Create Folders", flat=True, checkable=True)
        layout = QGridLayout(self.folders_groupbox)
        layout.addWidget(QLabel("Count"), 0, 0)
        layout.addWidget(self.num_folders_count_spinbox, 0, 1)
        layout.addWidget(QLabel("Name"), 1, 0)
        layout.addWidget(self.name_of_folders_entry_lineedit, 1, 1)
        layout.addWidget(self.is_make_folders_unique_checkbox, 2, 0, 1, 2)

    def setup_filename_ui(self) -> None:
        """Set up the filename UI components."""
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
        layout = QGridLayout(self.filename_groupbox)
        layout.addWidget(keep_filename, 0, 0, 1, 2)
        layout.addWidget(self.index_filename_radio, 1, 0, 1, 2)
        layout.addWidget(self.rename_filename_radio, 2, 0)
        layout.addWidget(self.rename_filename_entry, 2, 1)

    def setup_trash_ui(self) -> None:
        """Set up the trash UI components."""
        self.is_trash_empty = QCheckBox("Empty Folders")
        self.is_trash_source = QCheckBox("Valid Files")
        self.is_trash_invalid = QCheckBox("Invalid Files")

        self.trash_groupbox = QGroupBox(title="Trash", flat=True, checkable=True)
        layout = QVBoxLayout(self.trash_groupbox)
        layout.addWidget(self.is_trash_empty)
        layout.addWidget(self.is_trash_source)
        layout.addWidget(self.is_trash_invalid)

    def setup_setup_section(self) -> None:
        """Set up the setup tab UI components."""
        self.setup_file_count_ui()
        self.setup_root_ui()
        self.setup_dest_ui()
        self.setup_create_folders_ui()
        self.setup_filename_ui()
        self.setup_trash_ui()

        self.setup_section = QWidget()
        layout = QGridLayout(self.setup_section)
        layout.addWidget(self.file_count_groupbox, 0, 0, 1, 6)
        layout.addWidget(self.root_groupbox, 1, 0, 1, 3)
        layout.addWidget(self.dest_groupbox, 1, 3, 1, 3)
        layout.addWidget(self.folders_groupbox, 2, 0, 1, 2)
        layout.addWidget(self.filename_groupbox, 2, 2, 1, 2)
        layout.addWidget(self.trash_groupbox, 2, 4, 1, 2)

    # FILTER SECTION

    def setup_keywords_ui(self) -> None:
        """Set up the keywords UI components."""
        self.included_keys_lineedit = QLineEdit()
        self.included_keys_groupbox = QGroupBox(title="Include", checkable=True, flat=True)
        inc_keys_l = QHBoxLayout(self.included_keys_groupbox)
        inc_keys_l.addWidget(self.included_keys_lineedit)

        self.excluded_keys_lineedit = QLineEdit()
        self.excluded_keys_groupbox = QGroupBox(title="Exclude", checkable=True, flat=True)
        exc_keys_l = QHBoxLayout(self.excluded_keys_groupbox)
        exc_keys_l.addWidget(self.excluded_keys_lineedit)

        switch_keywords_button = QPushButton("Switch")
        switch_keywords_button.clicked.connect(self.switch_keywords)

        self.keywords_groupbox = QGroupBox(title="Keywords", flat=True)
        layout = QGridLayout(self.keywords_groupbox)
        layout.addWidget(self.included_keys_groupbox, 0, 0)
        layout.addWidget(self.excluded_keys_groupbox, 1, 0)
        layout.addWidget(switch_keywords_button, 0, 1, 2, 1)

    def setup_extensions_ui(self) -> None:
        """Set up the extensions UI components."""
        self.included_extensions_lineedit = QLineEdit()
        self.included_extensions_groupbox = QGroupBox(title="Include", checkable=True, flat=True)
        inc_exts_l = QHBoxLayout(self.included_extensions_groupbox)
        inc_exts_l.addWidget(self.included_extensions_lineedit)

        self.excluded_extensions_lineedit = QLineEdit()
        self.excluded_extensions_groupbox = QGroupBox(title="Exclude", checkable=True, flat=True)
        exc_exts_l = QHBoxLayout(self.excluded_extensions_groupbox)
        exc_exts_l.addWidget(self.excluded_extensions_lineedit)

        switch_extensions_button = QPushButton("Switch")
        switch_extensions_button.clicked.connect(self.switch_extensions)

        self.extensions_groupbox = QGroupBox(title="Extensions", flat=True)
        layout = QGridLayout(self.extensions_groupbox)
        layout.addWidget(self.included_extensions_groupbox, 0, 0)
        layout.addWidget(self.excluded_extensions_groupbox, 1, 0)
        layout.addWidget(switch_extensions_button, 0, 1, 2, 1)

    def setup_size_ui(self) -> None:
        """Set up the size UI components."""
        self.sizeLo = QDoubleSpinBox()
        self.sizeLo.setRange(0, 100000)
        self.sizeLo.editingFinished.connect(self.switch_size)

        self.sizeHi = QDoubleSpinBox()
        self.sizeHi.setRange(1, 100000)
        self.sizeHi.setValue(50)
        self.sizeHi.editingFinished.connect(self.switch_size)

        self.sizeType = QComboBox()
        self.sizeType.addItems(("B", "KB", "MB", "GB"))
        self.sizeType.setCurrentIndex(2)

        self.size_groupbox = QGroupBox(title="Size", flat=True, checkable=True)
        layout = QGridLayout(self.size_groupbox)
        layout.addWidget(QLabel("Min:"), 0, 0)
        layout.addWidget(self.sizeLo, 0, 1)
        layout.addWidget(QLabel("Max:"), 1, 0)
        layout.addWidget(self.sizeHi, 1, 1)
        layout.addWidget(self.sizeType, 0, 2, 2, 1)

    def setup_duration_ui(self) -> None:
        """Set up the duration UI components."""
        self.duration_low_dblspin = QDoubleSpinBox()
        self.duration_low_dblspin.setRange(0, 100000)
        self.duration_low_dblspin.setAccelerated(True)
        self.duration_low_dblspin.setGroupSeparatorShown(True)
        self.duration_low_dblspin.setFrame(True)
        self.duration_low_dblspin.editingFinished.connect(self.switch_duration)

        self.duration_high_dblspin = QDoubleSpinBox()
        self.duration_high_dblspin.setRange(1, 100000)
        self.duration_high_dblspin.setAccelerated(True)
        self.duration_high_dblspin.setGroupSeparatorShown(True)
        self.duration_high_dblspin.setValue(100)
        self.duration_high_dblspin.editingFinished.connect(self.switch_duration)

        self.duration_combobox = QComboBox()
        self.duration_combobox.addItems(("s", "m"))
        self.duration_combobox.setCurrentIndex(0)

        self.duration_groupbox = QGroupBox(title="Duration", flat=True, checkable=True)
        layout = QGridLayout(self.duration_groupbox)
        layout.addWidget(QLabel("Min:"), 0, 0)
        layout.addWidget(self.duration_low_dblspin, 0, 1)
        layout.addWidget(QLabel("Max:"), 1, 0)
        layout.addWidget(self.duration_high_dblspin, 1, 1)
        layout.addWidget(self.duration_combobox, 0, 2, 2, 1)

    def setup_weight_ui(self) -> None:
        """Set up the weight UI components."""
        self.weight_top_spinbox = create_spinbox(0, 100000, enabled=True)
        self.weight_top_spinbox.setSpecialValueText("None")

        self.weight_bottom_spinbox = create_spinbox(0, 100000, enabled=True)
        self.weight_bottom_spinbox.setSpecialValueText("None")

        self.weight_groupbox = QGroupBox(title="Weight", flat=True, checkable=True)
        layout = QGridLayout(self.weight_groupbox)
        layout.addWidget(QLabel("Top"), 0, 0)
        layout.addWidget(self.weight_top_spinbox, 0, 1)
        layout.addWidget(QLabel("Bottom"), 1, 0)
        layout.addWidget(self.weight_bottom_spinbox, 1, 1)

    def setup_filter_section(self) -> None:
        """Set up the customize tab UI components."""
        self.setup_size_ui()
        self.setup_weight_ui()
        self.setup_duration_ui()
        self.setup_keywords_ui()
        self.setup_extensions_ui()

        self.filter_section = QWidget()
        layout = QGridLayout(self.filter_section)
        layout.addWidget(self.keywords_groupbox, 0, 0, 1, 3)
        layout.addWidget(self.extensions_groupbox, 1, 0, 1, 3)
        layout.addWidget(self.size_groupbox, 2, 0)
        layout.addWidget(self.duration_groupbox, 2, 1)
        layout.addWidget(self.weight_groupbox, 2, 2)

    # RUN SECTION

    def setup_run_section(self) -> None:
        """Set up the run section UI components."""
        # PROGRESS BAR
        self.progressBar = QProgressBar(
            value=0,
            format="%v",
            textVisible=True,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        # RUN BUTTON
        self.runButton = QPushButton("Start")
        self.runButton.clicked.connect(self.run_mandala_push)

        # STOP BUTTON
        self.stopButton = QPushButton("Stop")
        self.stopButton.clicked.connect(self.stop_mandala_push)
        self.stopButton.setVisible(False)
        self.stopTracker = False

        # STALL TIMER BAR DISPLAY
        self.stallTimeSpinBox = QDoubleSpinBox()
        self.stallTimeSpinBox.setRange(1, 600000)
        self.stallTimeSpinBox.setValue(10)
        self.stallTimeSpinBox.setDecimals(1)
        self.stallTimeSpinBox.setSuffix(" s")
        self.stallTimeSpinBox.valueChanged.connect(self.change_stall_time_spinbox)
        self.stallLimit = self.stallTimeSpinBox.value()

        self.stallTimeProgressBar = QProgressBar(textVisible=False)
        self.stallTimeProgressBar.setMaximumHeight(8)

        self.stallTimeCounter = QLabel(f"{self.stallLimit}0 s")
        self.stallTimeCounter.setVisible(False)

        self.logBlock = QTextBrowser()
        self.logBlock.setMinimumHeight(175)
        self.logBlock.setMaximumHeight(175)
        self.logBlock.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        self.timer = QTimer()
        self.timer.setSingleShot(False)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.update_timer)

        self.run_section = QWidget()
        layout = QGridLayout(self.run_section)
        layout.addWidget(self.logBlock, 0, 0, 1, 3)
        layout.addWidget(self.stallTimeProgressBar, 1, 0)
        layout.addWidget(self.stallTimeSpinBox, 1, 1)
        layout.addWidget(self.stallTimeCounter, 1, 2)
        layout.addWidget(self.progressBar, 2, 0)
        layout.addWidget(self.runButton, 2, 1)
        layout.addWidget(self.stopButton, 2, 2)

    # SIDEBAR SECTION

    def setup_sidebar_section(self) -> None:
        """Set up the sidebar UI components."""
        self.show_invalid = QCheckBox("Log Invalid")
        self.show_invalid.setChecked(True)

        self.show_help = QCheckBox("Show Help")
        self.show_help.stateChanged.connect(self.set_filecount_tooltip)
        self.show_help.stateChanged.connect(self.set_randomize_filecount_tooltip)
        self.show_help.setChecked(True)

        open_root_button = QPushButton("Root")
        open_root_button.clicked.connect(lambda: os.startfile(self.root))

        open_dest_button = QPushButton("Destination")
        open_dest_button.clicked.connect(lambda: os.startfile(self.dest))

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_config)

        load_button = QPushButton("Load")
        load_button.clicked.connect(self.load_config)

        default_button = QPushButton("Set Default")
        default_button.clicked.connect(lambda: self.save_gui(self.settings))

        reset_button = QPushButton("Reset to Default")
        reset_button.clicked.connect(lambda: self.restore_gui(self.settings))

        self.sidebar_section = QWidget()
        layout = QVBoxLayout(self.sidebar_section)
        layout.addWidget(load_button)
        layout.addWidget(save_button)
        layout.addWidget(open_root_button)
        layout.addWidget(open_dest_button)
        layout.addWidget(default_button)
        layout.addWidget(reset_button)
        layout.addStretch()
        layout.addWidget(self.show_help)
        layout.addWidget(self.show_invalid)

    # SETUP UI

    def setup_ui(self) -> None:
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

    # TOOLTIPS

    @Slot()
    def set_filecount_tooltip(self) -> None:
        """Set the tooltip for the file count group box."""
        is_random_files = self.random_file_count_groupbox.isChecked()
        num_files_lo = self.min_num_files.value()
        num_files_hi = self.max_num_files.value()
        is_show_help = self.show_help.isChecked()

        if is_show_help and not is_random_files:
            self.file_count_groupbox.setToolTip(
                f"{NOWRAP}<font size=4><b>{num_files_lo}</b> file(s) will be copied from "
                f"<b>{self.root}</b> to <b>{self.dest}</b>"
            )
        elif is_show_help and is_random_files and (num_files_lo <= num_files_hi):
            self.file_count_groupbox.setToolTip(
                f"{NOWRAP}<font size=4><b>{num_files_lo}</b> to "
                f"<b>{num_files_hi}</b> files will be copied from <b>{self.root}</b> to <b>{self.dest}</b>"
            )
        elif is_show_help and is_random_files and (num_files_hi < num_files_lo):
            self.file_count_groupbox.setToolTip(
                f"{NOWRAP}<font size=4><b>{num_files_hi}</b> to "
                f"<b>{num_files_lo}</b> files will be copied from <b>{self.root}</b> to <b>{self.dest}</b>"
            )
        else:
            self.file_count_groupbox.setToolTip("")

    @Slot()
    def set_randomize_filecount_tooltip(self) -> None:
        """Set the tooltip for the randomize file group box."""
        is_random_files = self.random_file_count_groupbox.isChecked()
        num_files_lo = self.min_num_files.value()
        num_files_hi = self.max_num_files.value()
        is_show_help = self.show_help.isChecked()

        if is_show_help and not is_random_files:
            self.random_file_count_groupbox.setToolTip(
                f"{NOWRAP}<font size=5><i>Randomize</i></font>"
                f"\n<font size=4>    Uses a randomly selected number between the "
                f"left ({num_files_lo}) and right ({num_files_hi}) boxes as the file count\n"
                f"<b>    Uses the number in the left ({num_files_lo}) box as the file count </b>"
            )
        elif is_show_help and is_random_files:
            self.random_file_count_groupbox.setToolTip(
                f"{NOWRAP}<font size=5><i>Randomize</i></font><font size=4>\n"
                f"\n    <b>Uses a randomly selected number between the "
                f"left ({num_files_lo}) and right ({num_files_hi}) boxes as the file count</b>\n"
                f"    Uses the number in the left ({num_files_lo}) box as the file count"
            )
        else:
            self.random_file_count_groupbox.setToolTip("")

    ### ROOT AND DESTINATION METHODS ###

    def reset_path_to_start(self) -> Path:
        """Reset the current working directory to the start root path."""
        os.chdir(self.root)
        return Path.cwd()

    @Slot()
    def change_root(self) -> None:
        """Change the root path based on the combo box selection."""
        self.root = Path(self.root_combobox.currentText())

    @Slot()
    def change_destination(self) -> None:
        """Change the destination path based on the combo box selection."""
        self.dest = Path(self.dest_combobox.currentText())

    @Slot()
    def browse_root(self) -> None:
        """Browse for a new root directory."""
        self.root_directory = QFileDialog.getExistingDirectory(self, "Select Root Folder", str(self.root))

        if self.root_directory:
            if self.root_combobox.findText(self.root_directory) == -1:
                self.root_combobox.addItem(self.root_directory)
            self.root_combobox.setCurrentIndex(self.root_combobox.findText(self.root_directory))
            self.root = Path(self.root_directory)

    @Slot()
    def browse_destination(self) -> None:
        """Browse for a new destination directory."""
        self.dest_directory = QFileDialog.getExistingDirectory(self, "Select Destination Folder", str(self.dest))
        if self.dest_directory:
            if self.dest_combobox.findText(self.dest_directory) == -1:
                self.dest_combobox.addItem(self.dest_directory)
            self.dest_combobox.setCurrentIndex(self.dest_combobox.findText(self.dest_directory))
            self.dest = Path(self.dest_directory)

    @Slot()
    def delete_root_item(self) -> None:
        """Delete the current root item from the combo box."""
        if self.root_combobox.count() == 1:
            return
        self.root_combobox.removeItem(self.root_combobox.currentIndex())

    @Slot()
    def delete_dest_item(self) -> None:
        """Delete the current destination item from the combo box."""
        if self.dest_combobox.count() == 1:
            return
        self.dest_combobox.removeItem(self.dest_combobox.currentIndex())

    ### RUN METHODS ###

    def init_global_vars(self) -> None:
        """Initialize global variables."""
        self.touchedFiles = defaultdict(bool)
        self.touchedFolders = defaultdict(bool)
        self.touchedByWeight = defaultdict(bool)
        self.weighted = defaultdict(int)
        self.keywords = []
        self.notKeywords = []
        self.extensions = []
        self.notExtensions = []
        self.topWeightValue = 0
        self.bottomWeightValue = 0
        self.numFolders = 1
        self.indexFiles = False
        self.renameFiles = False
        self.renameName = ""

    def assign_global_vars(self) -> None:
        """Assign global variables based on the current UI settings."""
        self.init_global_vars()
        # File Count Variables
        self.numberOfFiles = self.num_file_count.value()

        # Root and Destination
        self.root = Path(self.root_combobox.currentText())
        self.dest = Path(self.dest_combobox.currentText())

        # Keyword Variables
        if self.included_keys_groupbox.isChecked():
            self.keywords = convert_string_to_list(self.included_keys_lineedit.text())

        if self.excluded_keys_groupbox.isChecked():
            self.notKeywords = convert_string_to_list(self.excluded_keys_lineedit.text())

        # Extension Variables
        if self.included_extensions_groupbox.isChecked():
            self.extensions = convert_string_to_list(self.included_extensions_lineedit.text())

        if self.excluded_extensions_groupbox.isChecked():
            self.notExtensions = convert_string_to_list(self.excluded_extensions_lineedit.text())

        # File Size Variables
        self.isRemoveSizeLimit = not self.size_groupbox.isChecked()
        if not self.isRemoveSizeLimit:
            self.minSize = self.sizeLo.value()
            self.maxSize = self.sizeHi.value()
            self.convert_to_bytes()

        # File Length Variables
        self.isRemoveLengthLimit = not self.duration_groupbox.isChecked()
        if not self.isRemoveLengthLimit:
            self.maxDuration = self.duration_high_dblspin.value()
            self.minDuration = self.duration_low_dblspin.value()
            self.convert_minutes_to_seconds()

        # Weight Variables
        if self.weight_groupbox.isChecked():
            self.topWeightValue = self.weight_top_spinbox.value()
            self.bottomWeightValue = self.weight_bottom_spinbox.value()

        # Folder Variables
        self.makeFoldersUnique = self.is_make_folders_unique_checkbox.isChecked()
        self.nameOfFolders = self.name_of_folders_entry_lineedit.text()
        self.isCreateFolders = self.folders_groupbox.isChecked()

        # Folder Count
        if self.isCreateFolders:
            self.numFolders = self.num_folders_count_spinbox.value()

        # Filename Variables
        if self.filename_groupbox.isChecked():
            self.indexFiles = self.index_filename_radio.isChecked()
            self.renameFiles = self.rename_filename_radio.isChecked()
            self.renameName = self.rename_filename_entry.text()

        # Trash Variables
        self.trashEmptyFolders = False
        self.trashSourceFiles = False
        self.trashInvalidFiles = False
        if self.trash_groupbox.isChecked():
            self.trashEmptyFolders = self.is_trash_empty.isChecked()
            self.trashSourceFiles = self.is_trash_source.isChecked()
            self.trashInvalidFiles = self.is_trash_invalid.isChecked()

        self.startAbsolute = self.root.resolve()
        self.isAppendLog = False
        self.count = 0
        self.bytesInCurrentFolder = 0
        self.startFolderTime = perf_counter()
        self.startStallTime = perf_counter()

    def run_mandala(self) -> None:
        """Run the main file copying process."""
        self.assign_global_vars()

        for _ in range(self.numFolders):
            if self.stopTracker:
                self.stop_mandala()
                return

            self.process_folder()

        self.stop_mandala()

    def process_folder(self) -> None:
        """Process a single folder for file copying."""
        # If you don't want unique folders, clear the touched dictionaries and restart
        self.touchedFiles = defaultdict(bool)
        self.touchedFolders = defaultdict(bool)
        if self.makeFoldersUnique:
            self.touchedFolders[self.startAbsolute] = False
            for key in self.touchedByWeight:
                self.touchedFiles[key] = False
                self.touchedFolders[key] = False

        self.dest = Path(self.dest_combobox.currentText())

        top_weight_mark = Path()
        self.weighted = defaultdict(int)
        self.touchedByWeight = defaultdict(bool)

        self.bytesInCurrentFolder = 0
        self.count = 0
        self.dest = self.create_folders(self.dest)

        dummy_file = Path(self.log.name + ".tmp")
        self.dummyLog = dummy_file.open("a", encoding="utf-8")

        self.startFolderTime = perf_counter()
        self.startStallTime = perf_counter()
        main_path = self.reset_path_to_start()

        # File Count
        if self.random_file_count_groupbox.isChecked():
            self.numberOfFiles = random.randint(self.min_num_files.value(), self.max_num_files.value())

        self.progressBar.setRange(0, self.numberOfFiles)

        for curr_file in range(self.numberOfFiles):
            if self.stopTracker:
                self.stop_mandala()
                return

            if self.touchedFolders[self.startAbsolute] and self.is_timed_out(self.startStallTime):
                break

            main_path = self.process_file(main_path, top_weight_mark, curr_file)

        #########################  END OF FOLDER  #########################
        self.end_folder_actions()

    def process_file(self, main_path: Path, top_weight_mark: Path, curr_file: int) -> Path:
        """Process a single file for copying."""
        while not self.touchedFolders[self.startAbsolute] and not self.is_timed_out(self.startStallTime):
            if self.stopTracker:
                self.stop_mandala()
                return main_path

            main_path_absolute = main_path.resolve()
            # Try to get main path
            try:
                if not self.listOfPaths[main_path_absolute]:
                    self.listOfPaths[main_path_absolute] = list(main_path.iterdir())
            except PermissionError:
                self.touchedFolders[main_path_absolute] = True
                main_path = self.reset_path_to_start()
                continue

            # If folder is empty
            if len(self.listOfPaths[main_path_absolute]) == 0:
                self.touchedFolders[main_path_absolute] = True
                if self.trashEmptyFolders:
                    send2trash.send2trash(str(main_path_absolute))
                main_path = self.reset_path_to_start()
            # If the folder is not empty
            else:
                # Chooses random path and stores absolute path
                random_path = Path(random.choice(self.listOfPaths[main_path_absolute]))
                random_path_absolute = random_path.resolve()
                # If touched, try again:
                if self.touchedFiles[random_path_absolute] or self.touchedFolders[random_path_absolute]:
                    self.touch_folder_if_all_files_touched(self.listOfPaths[main_path_absolute], main_path_absolute)
                    main_path = self.reset_path_to_start()
                elif random_path.is_dir():
                    main_path, top_weight_mark = self.handle_random_path_is_dir(
                        random_path, random_path_absolute, main_path, top_weight_mark
                    )
                elif random_path.is_file():
                    # Touch the file and get size
                    self.touchedFiles[random_path_absolute] = True
                    random_path_size = Path(random_path).stat().st_size
                    random_path_relative = Path(os.path.relpath(random_path, self.root))
                    # If file is valid
                    if self.is_valid_file(random_path, random_path_size) and self.copy_files_to_target(
                        curr_file, random_path, Path(self.dest), random_path_size
                    ):
                        self.handle_log(random_path_relative, curr_file)
                        self.bytesInCurrentFolder += random_path_size
                        self.count += 1
                        self.signals.count_signal.emit()
                        self.startStallTime = perf_counter()
                        self.signals.time_signal.emit()
                        if self.trashSourceFiles:
                            send2trash.send2trash(str(random_path_absolute))

                        self.handle_weights(top_weight_mark, main_path_absolute)
                        main_path = self.reset_path_to_start()
                        break

                    # If file is invalid
                    self.handle_invalid_file(random_path_relative, random_path_absolute)
                    main_path = self.reset_path_to_start()
        return main_path

    def handle_log(self, random_path: Path, curr_file: int) -> None:
        """Handle logging of valid files."""
        if not self.isAppendLog:
            self.log.write(f"{curr_file + 1}: {random_path}\n")
            self.signals.log_signal.emit(f"{curr_file + 1}: {random_path}")
        else:
            self.dummyLog.write(f"{curr_file + 1}: {random_path}\n")
            self.signals.log_signal.emit(f"{curr_file + 1}: {random_path}")

    def handle_invalid_file(self, random_path: Path, random_path_absolute: Path) -> None:
        """Handle invalid files by logging and trashing if necessary."""
        if self.show_invalid.isChecked() and self.count < 100:
            self.signals.log_signal.emit(f"**: {random_path}")
        elif self.show_invalid.isChecked() and self.count >= 100:
            self.signals.log_signal.emit(f"***: {random_path}")
        elif self.show_invalid.isChecked() and self.count >= 1000:
            self.signals.log_signal.emit(f"****: {random_path}")

        if self.trashInvalidFiles:
            send2trash.send2trash(str(random_path_absolute))

    def handle_weights(self, top_weight_mark: Path, main_path_absolute: Path) -> None:
        """Handle weight assignments for folders."""
        if self.topWeightValue > 0:
            self.weighted[top_weight_mark] += 1
            if self.weighted[top_weight_mark] == self.topWeightValue:
                self.touchedFolders[top_weight_mark] = True
                self.touchedByWeight[top_weight_mark] = True

        if self.bottomWeightValue > 0:
            self.weighted[main_path_absolute] += 1
            if self.weighted[main_path_absolute] == self.bottomWeightValue:
                self.touchedFolders[main_path_absolute] = True
                self.touchedByWeight[main_path_absolute] = True

    def handle_random_path_is_dir(
        self, random_path: Path, random_path_absolute: Path, main_path: Path, top_weight_mark: Path
    ) -> tuple[Path, Path]:
        """Handle the case when the random path is a directory."""
        try:
            os.chdir(random_path)
            main_path = Path.cwd()
            if self.topWeightValue > 0 and Path(random_path_absolute).parent == self.root:
                top_weight_mark = random_path_absolute
        except PermissionError:
            self.touchedFolders[random_path_absolute] = True
            main_path = self.reset_path_to_start()
        return main_path, top_weight_mark

    def end_folder_actions(self) -> None:
        """Create and write log at the end of folder."""
        self.dummyLog.close()
        self.log.close()
        self.signals.log_signal.emit(self.write_status_log())
        # Terminates the program if no files were collected
        if self.count == 0:
            if self.isCreateFolders:
                shutil.rmtree(self.dest)
            elif not (self.isCreateFolders or self.isAppendLog):
                Path(self.log.name).unlink()

    def is_valid_file(self, source: Path, size: int) -> bool:
        """Check if a file is valid based on the current filters."""
        # If no limit, all valid, else checks valid size range. Returns immediately if neither
        if not (self.isRemoveSizeLimit or self.minSize <= size <= self.maxSize):
            return False

        # If a blacklist extension or keyword is found, immediately return invalid
        for not_extension in self.notExtensions:
            if re.compile(rf"\.{not_extension}$", re.IGNORECASE).search(source.suffix) is not None:
                return False

        for not_keyword in self.notKeywords:
            if re.compile(rf"(.*){not_keyword}(.*)", re.IGNORECASE).search(source.stem) is not None:
                return False

        is_within_size_range = True

        # If no extension or keyword, all valid.
        # If whitelist item found, immediately breaks
        is_extension = self.is_extension(source)
        is_keyword = self.is_keyword(source)

        # If a duration can be get it will be checked, otherwise skips
        is_within_duration = self.is_within_duration(source)

        # Checks that everything is True
        return is_extension and is_keyword and is_within_size_range and is_within_duration

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

    def is_within_duration(self, source: Path) -> bool:
        """Check if a file is within the specified duration range."""
        is_within_duration = False
        if self.isRemoveLengthLimit:
            is_within_duration = True
        else:
            try:
                sound = soundfile.SoundFile(source)
                duration = len(sound) / sound.samplerate
                if self.minDuration <= duration <= self.maxDuration:
                    is_within_duration = True
                else:
                    return False
            except RuntimeError:
                if source.suffix == ".mp3":
                    try:
                        duration = MP3(source).info.length
                        if self.minDuration <= duration <= self.maxDuration:
                            is_within_duration = True
                        else:
                            return False
                    except ValueError:
                        is_within_duration = True
                else:
                    is_within_duration = True
            except ValueError:
                is_within_duration = True
        return is_within_duration

    def copy_files_to_target(self, file_num: int, source: Path, dest: Path, source_size: int) -> bool | None:
        """Copy files to the target destination with appropriate naming."""
        source_absolute = source.resolve()
        source_name = source.name
        try:
            if self.indexFiles:
                shutil.copy(source_absolute, dest / f"{file_num + 1}.{source_name}")
            elif self.renameFiles:
                if not (dest / f"{self.renameName} {file_num + 1}{source.suffix}").exists():
                    shutil.copy(source_absolute, dest / f"{self.renameName} {file_num + 1}{source.suffix}")
                else:
                    x = 1
                    while (dest / f"{self.renameName} {file_num + x}{source.suffix}").exists():
                        x += 1
                    shutil.copy(source_absolute, dest / f"{self.renameName} {file_num + x}{source.suffix}")
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

    def create_folders(self, target: Path) -> Path:
        """Create folders in the destination if specified."""
        if not self.isCreateFolders:
            if Path(target / f"!{target.name}_log.txt").exists():
                self.isAppendLog = True
            else:
                self.isAppendLog = False
            self.log = (target / f"!{target.name}_log.txt").open("a", encoding="utf-8")
        else:
            try:
                Path(f"{target}/{self.nameOfFolders}").mkdir()
                target = target / f"{self.nameOfFolders}"
                self.log = (target / f"!{self.nameOfFolders}_log.txt").open("a", encoding="utf-8")
            except FileExistsError:
                for x in range(len(list(target.iterdir()))):
                    try:
                        Path(f"{target}/{self.nameOfFolders} {x + 2}").mkdir()
                        target = target / f"{self.nameOfFolders} {x + 2}"
                        self.log = (target / f"!{self.nameOfFolders} {x + 2}_log.txt").open("a", encoding="utf-8")
                        break
                    except FileExistsError:
                        continue
        return target

    def touch_folder_if_all_files_touched(self, list_of_paths: list[Path], absolute_path: Path) -> None:
        """Mark folder as touched if all files inside are touched."""
        for file_folder in list_of_paths:
            path = file_folder.resolve()
            if self.touchedFiles[path] or self.touchedFolders[path]:
                pass
            else:
                return
        self.touchedFolders[absolute_path] = True

    ### PROGRESS, TIMER METHODS ###

    @Slot()
    def change_stall_time_spinbox(self) -> None:
        """Change the stall time limit based on the spin box value."""
        self.stallLimit = self.stallTimeSpinBox.value()
        self.stallTimeCounter.setText(f"{self.stallLimit}0 s")

    def is_timed_out(self, start_stall_time: float) -> bool:
        """Check if the process has timed out based on stall time."""
        end_stall_time = perf_counter()
        return end_stall_time - start_stall_time > self.stallLimit

    @Slot()
    def update_timer(self) -> None:
        """Update the stall time progress bar and counter."""
        self.stallTimeProgressBar.setValue(self.stallTimeProgressBar.value() - 1)
        self.stallTimeCounter.setText(f"{self.stallTimeProgressBar.value() / 100} s")

    @Slot()
    def run_mandala_push(self) -> None:
        """Start the mandala process and disable UI elements."""
        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QWidget) and name not in ["stopButton", "logBlock"]:
                self.wasEnabled[name] = obj.isEnabled()

        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QWidget) and name not in ["stopButton", "logBlock"]:
                obj.setEnabled(False)

        self.progressBar.reset()
        self.stallTimeProgressBar.setRange(0, int(self.stallLimit * 100))
        self.stallTimeProgressBar.setValue(self.stallTimeProgressBar.maximum())
        self.stallTimeCounter.setText(f"{self.stallTimeProgressBar.value() / 100} s")

        self.timer.start(10)

        self.runButton.setVisible(False)
        self.stopButton.setVisible(True)
        self.stallTimeCounter.setVisible(True)
        self.stallTimeSpinBox.setVisible(False)
        self.stopTracker = False

        self.threadpool.globalInstance().start(self.worker)

    @Slot()
    def stop_mandala_push(self) -> None:
        """Stop the mandala process."""
        self.stopTracker = True

    def stop_mandala(self) -> None:
        """Stop mandala process and reset UI elements."""
        self.signals.finished_signal.emit()

        self.dummyLog.close()
        self.log.close()
        self.signals.log_signal.emit(self.write_status_log())

        self.runButton.setVisible(True)
        self.stopButton.setVisible(False)
        self.stallTimeCounter.setVisible(False)
        self.stallTimeSpinBox.setVisible(True)
        self.stallTimeCounter.setText(f"{self.stallLimit}0 s")
        self.dest = Path(self.dest_combobox.currentText())
        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QWidget) and name not in ["stopButton", "logBlock"]:
                obj.setEnabled(self.wasEnabled[name])

    ### LOG METHODS ###

    def write_status_log(self) -> str:
        """Write the status log at the end of each folder."""
        end_folder_time = perf_counter()
        curr_date = datetime.now(tz=UTC).strftime("%B %d, %Y")
        curr_time = datetime.now(tz=UTC).strftime("%I:%M:%S%p")
        status = ""
        time_out = self.is_timed_out(self.startStallTime)

        if self.count == self.numberOfFiles:
            status = f"SUCCESS: {self.count}/{self.numberOfFiles} files copied"
        elif time_out and self.count == 0 and self.isCreateFolders:
            status = "NO FILES FOUND: timed out | folder deleted"
        elif self.touchedFolders[self.startAbsolute] and self.count == 0 and self.isCreateFolders:
            status = "NO FILES FOUND: all files searched | folder deleted"
        elif self.touchedFolders[self.startAbsolute]:
            status = f"ALL FILES SEARCHED: {self.count}/{self.numberOfFiles} files copied"
        elif time_out:
            status = f"TIMED OUT: {self.count}/{self.numberOfFiles} files copied"
        elif self.stopTracker:
            status = f"STOPPED: {self.count}/{self.numberOfFiles} files copied"
        status_log = f"""------------------------------------------------------------------------
{status}
------------------------------------------------------------------------
Date:\t\t{curr_date}
Time:\t\t{curr_time}
Start:\t\t{self.root}
Destination:\t{self.dest}
Extensions:\t{self.print_extensions()}
Keywords:\t{self.print_keywords()}
Total size:\t{convert_byte_to_size(self.bytesInCurrentFolder)}
Total runtime:\t{round(end_folder_time - self.startFolderTime, 2)}s
------------------------------------------------------------------------"""
        status_log_app = f"""------------------------------------------------------------------------
{status}
------------------------------------------------------------------------
Date:\t{curr_date}
Time:\t{curr_time}
Start:\t{self.root}
Destination:\t{self.dest}
Extensions:\t{self.print_extensions()}
Keywords:\t{self.print_keywords()}
Total size:\t{convert_byte_to_size(self.bytesInCurrentFolder)}
Total runtime:\t{round(end_folder_time - self.startFolderTime, 2)}s
------------------------------------------------------------------------"""
        self.prepend_status_to_log(status_log)
        return status_log_app

    def prepend_status_to_log(self, status: str) -> None:
        """Prepend the status to the log file."""
        dummy_file = Path(self.log.name + ".tmp")
        # IF ITS A NEW LOG, APPEND STATUS
        if not self.isAppendLog:
            with (
                (Path(self.log.name)).open(encoding="utf-8") as read_obj,
                dummy_file.open("w", encoding="utf-8") as write_obj,
            ):
                write_obj.write(status + "\n")
                for _entry in read_obj:
                    write_obj.write(_entry)
            Path(self.log.name).unlink()
            Path(dummy_file).rename(self.log.name)
        else:
            with (
                dummy_file.open(encoding="utf-8") as read_obj,
                (Path(self.log.name)).open("a", encoding="utf-8") as write_obj,
            ):
                write_obj.write(status + "\n")
                for _entry in read_obj:
                    write_obj.write(_entry)
            Path(dummy_file).unlink()

    def print_keywords(self) -> str:
        """Print keywords as a string."""
        keywords_status = ""
        for keyword in self.keywords:
            if keyword != self.keywords[-1]:
                keywords_status += '"' + keyword + '"' + ", "
            else:
                keywords_status += '"' + keyword + '"'
                return keywords_status
        return keywords_status

    def print_extensions(self) -> str:
        """Print extensions as a string."""
        extension_status = ""
        for extension in self.extensions:
            if extension != self.extensions[-1]:
                extension_status += "." + extension + ", "
            else:
                extension_status += "." + extension
                return extension_status
        return extension_status

    ### FILE COUNT METHODS ###

    @Slot()
    def switch_file_count(self) -> None:
        """Switch the file count low and high values."""
        if not self.random_file_count_groupbox.isChecked():
            return

        lo = self.min_num_files.value()
        hi = self.max_num_files.value()
        if lo > hi:
            self.min_num_files.setValue(hi)
            self.max_num_files.setValue(lo)

    @Slot()
    def change_file_label_rand(self) -> None:
        """Change file count group box based on random or count selection."""
        r = self.random_file_count_groupbox.isChecked()
        self.set_file_count_groupbox.setChecked(not r)

        for child in self.random_file_count_groupbox.children():
            if isinstance(child, QWidget):
                child.setEnabled(r)

        for child in self.set_file_count_groupbox.children():
            if isinstance(child, QWidget):
                child.setEnabled(not r)

    @Slot()
    def change_file_label_count(self) -> None:
        """Change file count group box based on random or count selection."""
        r = self.set_file_count_groupbox.isChecked()
        self.random_file_count_groupbox.setChecked(not r)

        for child in self.set_file_count_groupbox.children():
            if isinstance(child, QWidget):
                child.setEnabled(r)

        for child in self.random_file_count_groupbox.children():
            if isinstance(child, QWidget):
                child.setEnabled(not r)

    ### FILE SIZE METHODS ###

    @Slot()
    def switch_size(self) -> None:
        """Switch the size low and high values."""
        lo = self.sizeLo.value()
        hi = self.sizeHi.value()
        if lo > hi:
            self.sizeLo.setValue(hi)
            self.sizeHi.setValue(lo)

    def convert_to_bytes(self) -> None:
        """Convert size from KB, MB, or GB to bytes."""
        current_text = self.sizeType.currentText()

        if current_text == "B":
            self.minSize = round(self.sizeLo.value(), 2)
            self.maxSize = round(self.sizeHi.value(), 2)
        elif current_text == "KB":
            self.minSize = round(self.sizeLo.value() * BYTES_IN_KILOBYTE, 2)
            self.maxSize = round(self.sizeHi.value() * BYTES_IN_KILOBYTE, 2)
        elif current_text == "MB":
            self.minSize = round(self.sizeLo.value() * BYTES_IN_MEGABYTE, 2)
            self.maxSize = round(self.sizeHi.value() * BYTES_IN_MEGABYTE, 2)
        elif current_text == "GB":
            self.minSize = round(self.sizeLo.value() * BYTES_IN_GIGABYTE, 2)
            self.maxSize = round(self.sizeHi.value() * BYTES_IN_GIGABYTE, 2)

    ### FILE DURATION METHODS ###

    @Slot()
    def switch_duration(self) -> None:
        """Switch the duration low and high values."""
        lo = self.duration_low_dblspin.value()
        hi = self.duration_high_dblspin.value()
        if lo > hi:
            self.duration_low_dblspin.setValue(hi)
            self.duration_high_dblspin.setValue(lo)

    def convert_minutes_to_seconds(self) -> None:
        """Convert duration from minutes to seconds if needed."""
        if self.duration_combobox.currentText() == "m":
            self.minDuration = self.duration_low_dblspin.value() * SECONDS_IN_MINUTE
            self.maxDuration = self.duration_high_dblspin.value() * SECONDS_IN_MINUTE

    ### KEYWORDS AND EXTENSION METHODS ###

    @Slot()
    def switch_keywords(self) -> None:
        """Switch the include and exclude keywords."""
        include = self.included_keys_lineedit.text()
        exclude = self.excluded_keys_lineedit.text()
        self.included_keys_lineedit.setText(exclude)
        self.excluded_keys_lineedit.setText(include)

    @Slot()
    def switch_extensions(self) -> None:
        """Switch the include and exclude extensions."""
        include = self.included_extensions_lineedit.text()
        exclude = self.excluded_extensions_lineedit.text()
        self.included_extensions_lineedit.setText(exclude)
        self.excluded_extensions_lineedit.setText(include)

    ### SETTINGS METHODS ###

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Close event to save settings."""
        self.save_global_settings()

    def save_global_settings(self) -> None:
        """Save GUI settings to registry."""
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QCheckBox) and (name in ["show_invalid", "show_help"]):
                value = obj.isChecked()
                self.settings.setValue(name, value)

            if isinstance(obj, QTabWidget):
                value = obj.currentIndex()
                self.settings.setValue(name, value)

    def restore_global_settings(self) -> None:
        """Restore GUI settings from registry."""
        # Restore geometry
        size = self.settings.value("size", QSize(500, 500))
        if isinstance(size, QSize):
            self.resize(size)

        pos = self.settings.value("pos", QPoint(60, 60))
        if isinstance(pos, QPoint):
            self.move(pos)

        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QCheckBox) and (name in ["show_invalid", "show_help"]):
                value = self.settings.value(name)
                if value is not None:
                    obj.setChecked(strtobool(value))

            if isinstance(obj, QTabWidget):
                value = self.settings.value(name)
                if value is not None:
                    obj.setCurrentIndex(int(value))

    @Slot()
    def save_config(self) -> None:
        """Save GUI settings to registry."""
        save_file, _ = QFileDialog.getSaveFileName(
            self, "Save Current Configuration", "config.ini", ("Configuration (*.ini)")
        )
        if save_file:
            with Path(save_file).open("w", encoding="utf-8"):
                settings = QSettings(save_file, QSettings.Format.IniFormat)
                self.save_gui(settings)
            name = list(settings.fileName().split("/"))[-1][:-4]
            self.setWindowTitle(f"{name} - Mandala: Copy random files")

    @Slot()
    def load_config(self) -> None:
        """Load GUI settings from registry."""
        open_file, _ = QFileDialog.getOpenFileName(self, "Load Configuration", "", ("Configuration (*.ini)"))
        if open_file:
            with Path(open_file).open(encoding="utf-8"):
                settings = QSettings(open_file, QSettings.Format.IniFormat)
                self.restore_gui(settings)
            name = list(settings.fileName().split("/"))[-1][:-4]
            self.setWindowTitle(f"{name} - Mandala: Copy random files")

    @Slot()
    def save_gui(self, settings: QSettings) -> None:
        """Save GUI settings to registry."""
        for name, obj in inspect.getmembers(self):
            if isinstance(obj, QComboBox):
                items = [obj.itemText(i) for i in range(obj.count())]
                settings.setValue(name, items)  # save combobox selection to registry

                index = obj.currentIndex()  # get current index from combobox
                text = obj.itemText(index)  # get the text for current index
                settings.setValue(f"current{name}", text)

            if isinstance(obj, QLineEdit):
                value = obj.text()
                settings.setValue(name, value)  # save ui values, so they can be restored next time

            if isinstance(obj, QCheckBox) and name not in ["show_invalid", "show_help"]:
                state = obj.isChecked()
                settings.setValue(name, state)

            if isinstance(obj, QRadioButton):
                value = obj.isChecked()  # get stored value from registry
                settings.setValue(name, value)

            if isinstance(obj, QSpinBox):
                value = obj.value()
                settings.setValue(name, value)

            if isinstance(obj, QDoubleSpinBox):
                value = obj.value()
                settings.setValue(name, value)

            if isinstance(obj, QPushButton):
                value = obj.isChecked()
                settings.setValue(name, value)

    @Slot()
    def restore_gui(self, settings: QSettings) -> None:
        """Restore GUI settings from registry."""
        for name, obj in inspect.getmembers(self):
            value = settings.value(name)  # get stored value from registry

            if isinstance(obj, QComboBox):
                obj.clear()
                all_items = settings.value(name)
                if all_items is not None:
                    obj.addItems(all_items)

                value = settings.value(f"current{name}")
                if obj.findText(value) == -1:
                    obj.addItem(value)
                obj.setCurrentIndex(obj.findText(value))

            if isinstance(obj, QLineEdit):
                obj.setText(value)  # restore lineEditFile

            if isinstance(obj, QSpinBox) and value is not None:
                obj.setValue(int(value))

            if isinstance(obj, QDoubleSpinBox) and value is not None:
                obj.setValue(float(value))

            if (
                (isinstance(obj, QCheckBox) and name not in ("show_invalid", "show_help"))
                or (isinstance(obj, (QRadioButton, QPushButton)))
            ) and value is not None:
                try:
                    obj.setChecked(value)
                except TypeError:
                    obj.setChecked(strtobool(value))
