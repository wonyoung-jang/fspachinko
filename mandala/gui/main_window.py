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

import send2trash
import soundfile
from mutagen.mp3 import MP3
from PySide6.QtCore import QDir, QPoint, QSettings, QSize, Qt, QThreadPool, QTimer
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
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
    SECONDS_IN_MINUTE,
)
from ..gui.workers import RunMandalaWorker, WorkerSignals
from ..utilities.utils import convert_byte_to_size, convert_string_to_list, strtobool
from .qt_helpers import make_group_button, make_group_label, make_spinbox


class MainWindow(QWidget):
    """Main application window for Mandala."""

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.randomIcon = QIcon("icons/dices.svg")
        self.browseIcon = QIcon("icons/browse.svg")
        self.openIcon = QIcon("icons/open.svg")
        self.noWrap = '<p style="white-space:pre">'
        self.wasEnabled = {}
        self.listOfPaths = defaultdict(bool)

        self.threadpool = QThreadPool()
        self.mandala = RunMandalaWorker(self)
        self.mandala.setAutoDelete(False)

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

    def disable_group(self, button: QGroupBox | QPushButton, group: QWidget) -> None:
        """Enable or disable all children of a group based on the button state."""
        r = button.isChecked()
        for child in group.children():
            if isinstance(child, QWidget) and (child != button):
                child.setEnabled(r)

    # SETUP TAB

    def setup_file_count_ui(self) -> None:  # self.fileCountG
        """Set up the file count UI components."""
        self.fileCountLabel = QLabel("Count")
        self.fileLoLabel = QLabel("Min")
        self.fileLoLabel.setDisabled(True)

        self.fileHiLabel = QLabel("Max")
        self.fileHiLabel.setDisabled(True)

        self.numFilesCount = make_spinbox(1, 1000000000, enabled=True)
        self.numFilesLo = make_spinbox(1, 1000000000, enabled=False)
        self.numFilesHi = make_spinbox(2, 1000000000, enabled=False)

        self.countCheck = QRadioButton("Set Number")

        count_l = QHBoxLayout()
        count_l.addWidget(self.fileCountLabel)
        count_l.addWidget(self.numFilesCount)
        self.countFileG = QGroupBox("Set Number")
        self.countFileG.setLayout(count_l)
        self.countFileG.setCheckable(True)

        min_row = QHBoxLayout()
        min_row.addWidget(self.fileLoLabel)
        min_row.addWidget(self.numFilesLo)
        max_row = QHBoxLayout()
        max_row.addWidget(self.fileHiLabel)
        max_row.addWidget(self.numFilesHi)

        random_l = QVBoxLayout()
        random_l.addLayout(min_row)
        random_l.addLayout(max_row)
        self.randomFileG = QGroupBox("Randomize")
        self.randomFileG.setLayout(random_l)
        self.randomFileG.setCheckable(True)
        self.randomFileG.setChecked(False)

        file_count_l = QHBoxLayout()
        file_count_l.addWidget(self.countFileG)
        file_count_l.addWidget(self.randomFileG)

        self.fileCountG = QGroupBox("File count")
        self.fileCountG.setLayout(file_count_l)

        self.numFilesLo.editingFinished.connect(self.switch_file_count)
        self.numFilesHi.editingFinished.connect(self.switch_file_count)
        self.randomFileG.toggled.connect(self.switch_file_count)
        self.randomFileG.toggled.connect(self.change_file_label_rand)
        self.countFileG.toggled.connect(self.change_file_label_count)

    def setup_root_ui(self) -> None:  # self.rootG
        """Set up the root UI components."""
        self.rootLabel = make_group_label("Root")

        self.root = QDir.rootPath()
        self.rootDirectory = self.root

        self.rootCombo = QComboBox()
        self.rootCombo.addItem(self.root)

        self.browseRootButton = QPushButton(" Browse")
        self.browseRootButton.setIcon(self.browseIcon)

        self.deleteRoot = QPushButton("Delete")

        self.deleteRoot.clicked.connect(self.delete_root_item)
        self.rootCombo.currentTextChanged.connect(self.change_root)
        self.browseRootButton.clicked.connect(self.browse_root)

        root_controls = QHBoxLayout()
        root_controls.addWidget(self.rootCombo)
        root_controls.addWidget(self.browseRootButton)
        root_controls.addWidget(self.deleteRoot)

        root_l = QVBoxLayout()
        root_l.addWidget(self.rootLabel)
        root_l.addLayout(root_controls)

        self.rootG = QGroupBox()
        self.rootG.setLayout(root_l)

    def setup_dest_ui(self) -> None:  # self.destG
        """Set up the destination UI components."""
        self.destLabel = make_group_label("Destination")

        self.dest = QDir.homePath()
        self.destDirectory = self.dest

        self.destCombo = QComboBox()
        self.destCombo.addItem(self.dest)

        self.browseDestButton = QPushButton(" Browse")
        self.browseDestButton.setIcon(self.browseIcon)

        self.deleteDest = QPushButton("Delete")

        self.deleteDest.clicked.connect(self.delete_dest_item)
        self.destCombo.currentTextChanged.connect(self.change_destination)
        self.browseDestButton.clicked.connect(self.browse_destination)

        dest_label_l = QHBoxLayout()
        dest_label_l.addWidget(self.destLabel)
        dest_label_l.addStretch()

        dest_controls = QHBoxLayout()
        dest_controls.addWidget(self.destCombo)
        dest_controls.addWidget(self.browseDestButton)
        dest_controls.addWidget(self.deleteDest)

        dest_l = QVBoxLayout()
        dest_l.addLayout(dest_label_l)
        dest_l.addLayout(dest_controls)

        self.destG = QGroupBox()
        self.destG.setLayout(dest_l)

    def setup_create_folders_ui(self) -> None:  # self.foldersG
        """Set up the create folders UI components."""
        self.folderButton = make_group_button("Folders")

        self.folderCountLabel = QLabel("Count")
        folders_name_label = QLabel("Name")

        self.numFoldersCount = QSpinBox()
        self.numFoldersCount.setRange(1, 100000)

        self.nameOfFoldersEntry = QLineEdit("Folder Name")

        self.makeFoldersUniqueCheck = QCheckBox("Make Unique")
        self.makeFoldersUniqueCheck.setChecked(True)

        label_row = QHBoxLayout()
        label_row.addWidget(self.folderButton)
        label_row.addStretch()

        row1 = QHBoxLayout()
        row1.addWidget(self.folderCountLabel)
        row1.addWidget(self.numFoldersCount)

        row2 = QHBoxLayout()
        row2.addWidget(folders_name_label)
        row2.addWidget(self.nameOfFoldersEntry)

        folders_l = QVBoxLayout()
        folders_l.addLayout(label_row)
        folders_l.addLayout(row1)
        folders_l.addLayout(row2)
        folders_l.addWidget(self.makeFoldersUniqueCheck)

        self.foldersG = QGroupBox()
        self.foldersG.setLayout(folders_l)

        self.folderButton.toggled.connect(lambda: self.disable_group(self.folderButton, self.foldersG))

    def setup_filename_ui(self) -> None:  # self.fileNameG
        """Set up the filename UI components."""
        self.fileNameButton = make_group_button("Filenames")

        self.keepFilesRadio = QRadioButton("Keep")
        self.keepFilesRadio.setChecked(True)
        self.indexFilesRadio = QRadioButton("Index")
        self.renameFilesRadio = QRadioButton("Rename")
        self.renameNameEntry = QLineEdit("New Name")
        self.renameNameEntry.setEnabled(False)

        self.renameFilesRadio.toggled.connect(
            lambda: self.renameNameEntry.setEnabled(self.renameFilesRadio.isChecked())
        )

        label_row = QHBoxLayout()
        label_row.addWidget(self.fileNameButton)
        label_row.addStretch()

        rename_row = QHBoxLayout()
        rename_row.addWidget(self.renameFilesRadio)
        rename_row.addWidget(self.renameNameEntry)

        filename_l = QVBoxLayout()
        filename_l.addLayout(label_row)
        filename_l.addWidget(self.keepFilesRadio)
        filename_l.addWidget(self.indexFilesRadio)
        filename_l.addLayout(rename_row)

        self.fileNameG = QGroupBox()
        self.fileNameG.setLayout(filename_l)

        self.fileNameButton.toggled.connect(lambda: self.disable_group(self.fileNameButton, self.fileNameG))

    def setup_trash_ui(self) -> None:  # self.trashG
        """Set up the trash UI components."""
        self.trashButton = make_group_button("Trash")

        self.isTrashEmpty = QCheckBox("Empty Folders")
        self.isTrashSource = QCheckBox("Valid Files")
        self.isTrashInvalid = QCheckBox("Invalid Files")

        label_row = QHBoxLayout()
        label_row.addWidget(self.trashButton)
        label_row.addStretch()

        trash_l = QVBoxLayout()
        trash_l.addLayout(label_row)
        trash_l.addWidget(self.isTrashEmpty)
        trash_l.addWidget(self.isTrashSource)
        trash_l.addWidget(self.isTrashInvalid)

        self.trashG = QGroupBox()
        self.trashG.setLayout(trash_l)

        self.trashButton.toggled.connect(lambda: self.disable_group(self.trashButton, self.trashG))

    def setup_setup_tab(self) -> None:  # self.setupTab
        """Set up the setup tab UI components."""
        self.setup_file_count_ui()
        self.setup_root_ui()
        self.setup_dest_ui()
        self.setup_create_folders_ui()
        self.setup_filename_ui()
        self.setup_trash_ui()

        output_row = QHBoxLayout()
        output_row.addWidget(self.foldersG)
        output_row.addWidget(self.fileNameG)
        output_row.addWidget(self.trashG)

        setup_l = QVBoxLayout()
        setup_l.addWidget(self.fileCountG)
        setup_l.addWidget(self.rootG)
        setup_l.addWidget(self.destG)
        setup_l.addLayout(output_row)

        self.setupTab = QWidget()
        self.setupTab.setLayout(setup_l)

    # CUSTOMIZE TAB

    def setup_keywords_ui(self) -> None:  # self.keywordsG
        """Set up the keywords UI components."""
        self.incKeysEdit = QLineEdit()
        self.excKeysEdit = QLineEdit()

        self.toSwitchKeys = QPushButton("Switch")

        inc_keys_l = QHBoxLayout()
        inc_keys_l.addWidget(self.incKeysEdit)
        self.incKeysG = QGroupBox("Include")
        self.incKeysG.setLayout(inc_keys_l)
        self.incKeysG.setCheckable(True)

        exc_keys_l = QHBoxLayout()
        exc_keys_l.addWidget(self.excKeysEdit)
        self.excKeysG = QGroupBox("Exclude")
        self.excKeysG.setLayout(exc_keys_l)
        self.excKeysG.setCheckable(True)

        keywords_l = QHBoxLayout()
        keywords_l.addWidget(self.incKeysG)
        keywords_l.addWidget(self.toSwitchKeys)
        keywords_l.addWidget(self.excKeysG)

        self.keywordsG = QGroupBox("Keywords")
        self.keywordsG.setLayout(keywords_l)

        self.toSwitchKeys.clicked.connect(self.switch_keys)
        self.incKeysG.toggled.connect(lambda: self.disable_group(self.incKeysG, self.keywordsG))
        self.excKeysG.toggled.connect(lambda: self.disable_group(self.excKeysG, self.keywordsG))

    def setup_extensions_ui(self) -> None:  # self.extensionsG
        """Set up the extensions UI components."""
        self.incExtsEdit = QLineEdit()
        self.excExtsEdit = QLineEdit()

        self.toSwitchExts = QPushButton("Switch")

        inc_exts_l = QHBoxLayout()
        inc_exts_l.addWidget(self.incExtsEdit)
        self.incExtsG = QGroupBox("Include")
        self.incExtsG.setLayout(inc_exts_l)
        self.incExtsG.setCheckable(True)

        exc_exts_l = QHBoxLayout()
        exc_exts_l.addWidget(self.excExtsEdit)
        self.excExtsG = QGroupBox("Exclude")
        self.excExtsG.setLayout(exc_exts_l)
        self.excExtsG.setCheckable(True)

        extensions_l = QHBoxLayout()
        extensions_l.addWidget(self.incExtsG)
        extensions_l.addWidget(self.toSwitchExts)
        extensions_l.addWidget(self.excExtsG)

        self.extensionsG = QGroupBox("Extensions")
        self.extensionsG.setLayout(extensions_l)

        self.toSwitchExts.clicked.connect(self.switch_extensions)
        self.incExtsG.toggled.connect(lambda: self.disable_group(self.incExtsG, self.extensionsG))
        self.excExtsG.toggled.connect(lambda: self.disable_group(self.excExtsG, self.extensionsG))

    def setup_size_ui(self) -> None:  # self.sizeG
        """Set up the size UI components."""
        self.sizeButton = make_group_button("File Size")

        size_lo_label = QLabel("Min")
        size_hi_label = QLabel("Max")

        self.sizeLo = QDoubleSpinBox()
        self.sizeLo.setRange(0, 100000)

        self.sizeHi = QDoubleSpinBox()
        self.sizeHi.setRange(1, 100000)
        self.sizeHi.setValue(50)

        self.sizeType = QComboBox()
        self.sizeType.addItems(["B", "KB", "MB", "GB"])
        self.sizeType.setCurrentIndex(2)

        label_row = QHBoxLayout()
        label_row.addWidget(self.sizeButton)
        label_row.addStretch()

        row1 = QHBoxLayout()
        row1.addWidget(size_lo_label)
        row1.addWidget(self.sizeLo)

        row2 = QHBoxLayout()
        row2.addWidget(size_hi_label)
        row2.addWidget(self.sizeHi)
        row2.addWidget(self.sizeType)

        file_size_l = QVBoxLayout()
        file_size_l.addLayout(label_row)
        file_size_l.addLayout(row1)
        file_size_l.addLayout(row2)

        self.sizeG = QGroupBox()
        self.sizeG.setLayout(file_size_l)

        self.sizeLo.editingFinished.connect(self.switch_size)
        self.sizeHi.editingFinished.connect(self.switch_size)
        self.sizeButton.toggled.connect(lambda: self.disable_group(self.sizeButton, self.sizeG))

    def setup_duration_ui(self) -> None:  # self.durationG
        """Set up the duration UI components."""
        self.lengthButton = make_group_button("File Length")

        length_lo_label = QLabel("Min")
        length_hi_label = QLabel("Max")

        self.durationLo = QDoubleSpinBox()
        self.durationLo.setRange(0, 100000)
        self.durationLo.setAccelerated(True)
        self.durationLo.setGroupSeparatorShown(True)
        self.durationLo.setFrame(True)

        self.durationHi = QDoubleSpinBox()
        self.durationHi.setRange(1, 100000)
        self.durationHi.setAccelerated(True)
        self.durationHi.setGroupSeparatorShown(True)
        self.durationHi.setValue(100)

        self.durationType = QComboBox()
        self.durationType.addItems(["s", "m"])
        self.durationType.setCurrentIndex(0)

        label_row = QHBoxLayout()
        label_row.addWidget(self.lengthButton)
        label_row.addStretch()

        row1 = QHBoxLayout()
        row1.addWidget(length_lo_label)
        row1.addWidget(self.durationLo)

        row2 = QHBoxLayout()
        row2.addWidget(length_hi_label)
        row2.addWidget(self.durationHi)
        row2.addWidget(self.durationType)

        duration_l = QVBoxLayout()
        duration_l.addLayout(label_row)
        duration_l.addLayout(row1)
        duration_l.addLayout(row2)

        self.durationG = QGroupBox()
        self.durationG.setLayout(duration_l)

        self.durationLo.editingFinished.connect(self.switch_duration)
        self.durationHi.editingFinished.connect(self.switch_duration)
        self.lengthButton.toggled.connect(lambda: self.disable_group(self.lengthButton, self.durationG))

    def setup_weight_ui(self) -> None:  # self.weightG
        """Set up the weight UI components."""
        self.weightButton = make_group_button("Weight")

        top_weight_label = QLabel("Top")
        self.topWeightSpinBox = QSpinBox()
        self.topWeightSpinBox.setRange(0, 100000)
        self.topWeightSpinBox.setSpecialValueText("None")

        bottom_weight_label = QLabel("Bottom")
        self.bottomWeightSpinBox = QSpinBox()
        self.bottomWeightSpinBox.setRange(0, 100000)
        self.bottomWeightSpinBox.setSpecialValueText("None")

        label_row = QHBoxLayout()
        label_row.addWidget(self.weightButton)
        label_row.addStretch()

        row1 = QHBoxLayout()
        row1.addWidget(top_weight_label)
        row1.addWidget(self.topWeightSpinBox)

        row2 = QHBoxLayout()
        row2.addWidget(bottom_weight_label)
        row2.addWidget(self.bottomWeightSpinBox)

        weight_l = QVBoxLayout()
        weight_l.addLayout(label_row)
        weight_l.addLayout(row1)
        weight_l.addLayout(row2)

        self.weightG = QGroupBox()
        self.weightG.setLayout(weight_l)

        self.weightButton.toggled.connect(lambda: self.disable_group(self.weightButton, self.weightG))

    def setup_customize_tab(self) -> None:  # self.custTab
        """Set up the customize tab UI components."""
        self.setup_keywords_ui()
        self.setup_extensions_ui()
        self.setup_size_ui()
        self.setup_weight_ui()
        self.setup_duration_ui()

        row_l = QHBoxLayout()
        row_l.addWidget(self.sizeG)
        row_l.addWidget(self.durationG)
        row_l.addWidget(self.weightG)

        cust_l = QVBoxLayout()
        cust_l.addWidget(self.keywordsG)
        cust_l.addWidget(self.extensionsG)
        cust_l.addLayout(row_l)

        self.custTab = QWidget()
        self.custTab.setLayout(cust_l)

    # RUN SECTION

    def setup_run_section(self) -> None:  # self.runSection
        """Set up the run section UI components."""
        # PROGRESS BAR
        self.runLabel = QLabel("Run")
        self.stallLabel = QLabel("Timer")

        self.progressBar = QProgressBar()
        self.progressBar.setValue(0)
        self.progressBar.setFormat("%v")
        self.progressBar.setTextVisible(True)
        self.progressBar.setAlignment(Qt.AlignmentFlag.AlignCenter)

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

        self.stallTimeProgressBar = QProgressBar()
        self.stallTimeProgressBar.setMaximumHeight(8)
        self.stallTimeProgressBar.setTextVisible(False)

        self.stallTimeCounter = QLabel()
        self.stallTimeCounter.setText(f"{self.stallLimit}0 s")
        self.stallTimeCounter.setVisible(False)

        self.logLabel = QLabel("Log")

        self.logBlock = QTextBrowser()
        self.logBlock.setMinimumHeight(175)
        self.logBlock.setMaximumHeight(175)
        self.logBlock.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        self.timer = QTimer()
        self.timer.setSingleShot(False)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.update_timer)

        stall_row = QHBoxLayout()
        stall_row.addWidget(self.stallTimeProgressBar)
        stall_row.addWidget(self.stallTimeSpinBox)
        stall_row.addWidget(self.stallTimeCounter)

        run_row = QHBoxLayout()
        run_row.addWidget(self.progressBar)
        run_row.addWidget(self.runButton)
        run_row.addWidget(self.stopButton)

        self.runSection = QVBoxLayout()
        self.runSection.addWidget(self.logBlock)
        self.runSection.addLayout(stall_row)
        self.runSection.addLayout(run_row)

    # SIDEBAR SECTION

    def setup_sidebar_section(self) -> None:  # self.sideBar
        """Set up the sidebar UI components."""
        self.show_invalid = QCheckBox("Log Invalid")

        self.show_help = QCheckBox("Show Help")
        self.show_help.setChecked(True)

        self.show_help.stateChanged.connect(self.set_filecount_tooltip)
        self.show_help.stateChanged.connect(self.set_randomize_file_tooltip)

        self.openRoot = QPushButton("Root")
        self.openRoot.clicked.connect(lambda: os.startfile(self.root))

        self.openDest = QPushButton("Destination")
        self.openDest.clicked.connect(lambda: os.startfile(self.dest))

        self.openButton = QPushButton("Load")
        self.saveButton = QPushButton("Save")
        self.saveButton.clicked.connect(self.save_config)
        self.openButton.clicked.connect(self.load_config)

        self.defaultButton = QPushButton("Set Default")
        self.defaultButton.clicked.connect(lambda: self.save_gui(self.settings))
        self.resetButton = QPushButton("Reset to Default")
        self.resetButton.clicked.connect(lambda: self.restore_gui(self.settings))

        self.sideBar = QVBoxLayout()
        self.sideBar.addSpacing(20)
        self.sideBar.addWidget(self.openButton)
        self.sideBar.addWidget(self.saveButton)
        self.sideBar.addWidget(self.openRoot)
        self.sideBar.addWidget(self.openDest)
        self.sideBar.addWidget(self.defaultButton)
        self.sideBar.addWidget(self.resetButton)
        self.sideBar.addStretch()
        self.sideBar.addWidget(self.show_help)
        self.sideBar.addWidget(self.show_invalid)

    # SETUP UI

    def setup_ui(self) -> None:
        """Set up the main UI components."""
        self.setup_sidebar_section()
        self.setup_setup_tab()
        self.setup_customize_tab()
        self.setup_run_section()

        self.mainTabs = QTabWidget()
        self.mainTabs.setTabPosition(QTabWidget.TabPosition.North)
        self.mainTabs.setMovable(True)
        self.mainTabs.addTab(self.setupTab, "Setup")
        self.mainTabs.addTab(self.custTab, "Filter")

        master_row = QHBoxLayout()
        master_row.addWidget(self.mainTabs)
        master_row.addLayout(self.sideBar)

        master_layout = QVBoxLayout()
        master_layout.addLayout(master_row)
        master_layout.addLayout(self.runSection)

        self.setLayout(master_layout)
        self.setWindowTitle("Default - Copy Random Files")
        self.show()

    # TOOL TIPS

    def set_filecount_tooltip(self) -> None:
        """Set the tooltip for the file count group box."""
        is_random_files = self.randomFileG.isChecked()
        num_files_lo = self.numFilesLo.value()
        num_files_hi = self.numFilesHi.value()
        is_show_help = self.show_help.isChecked()

        if is_show_help and not is_random_files:
            self.fileCountG.setToolTip(
                f"{self.noWrap}<font size=4><b>{num_files_lo}</b> file(s) will be copied from"
                f"<b>{self.root}</b> to <b>{self.dest}</b>"
            )
        elif is_show_help and is_random_files and (num_files_lo <= num_files_hi):
            self.fileCountG.setToolTip(
                f"{self.noWrap}<font size=4><b>{num_files_lo}</b> to"
                f"<b>{num_files_hi}</b> files will be copied from <b>{self.root}</b> to <b>{self.dest}</b>"
            )
        elif is_show_help and is_random_files and (num_files_hi < num_files_lo):
            self.fileCountG.setToolTip(
                f"{self.noWrap}<font size=4><b>{num_files_hi}</b> to"
                f"<b>{num_files_lo}</b> files will be copied from <b>{self.root}</b> to <b>{self.dest}</b>"
            )
        else:
            self.fileCountG.setToolTip("")

    def set_randomize_file_tooltip(self) -> None:
        """Set the tooltip for the randomize file group box."""
        is_random_files = self.randomFileG.isChecked()
        num_files_lo = self.numFilesLo.value()
        num_files_hi = self.numFilesHi.value()
        is_show_help = self.show_help.isChecked()

        if is_show_help and not is_random_files:
            self.randomFileG.setToolTip(
                f"{self.noWrap}<font size=5><i>Randomize</i></font>\n<font size=4>"
                f"    Uses a randomly selected number between the "
                f"left ({num_files_lo}) and right ({num_files_hi}) boxes as the file count\n"
                f"<b>    Uses the number in the left ({num_files_lo}) box as the file count </b>"
            )
        elif is_show_help and is_random_files:
            self.randomFileG.setToolTip(
                f"{self.noWrap}<font size=5><i>Randomize</i></font><font size=4>\n"
                f"<b>    Uses a randomly selected number between the "
                f"left ({num_files_lo}) and right ({num_files_hi}) boxes as the file count</b>\n"
                f"    Uses the number in the left ({num_files_lo}) box as the file count"
            )
        else:
            self.randomFileG.setToolTip("")

    ### ROOT AND DESTINATION METHODS ###

    def reset_path_to_start(self) -> Path:
        """Reset the current working directory to the start root path."""
        os.chdir(self.root)
        return Path.cwd()

    def change_root(self) -> None:
        """Change the root path based on the combo box selection."""
        self.root = Path(self.rootCombo.currentText())

    def change_destination(self) -> None:
        """Change the destination path based on the combo box selection."""
        self.dest = Path(self.destCombo.currentText())

    def browse_root(self) -> None:
        """Browse for a new root directory."""
        self.rootDirectory = QFileDialog.getExistingDirectory(self, "Select Root Folder", str(self.root))

        if self.rootDirectory:
            if self.rootCombo.findText(self.rootDirectory) == -1:
                self.rootCombo.addItem(self.rootDirectory)
            self.rootCombo.setCurrentIndex(self.rootCombo.findText(self.rootDirectory))
            self.root = Path(self.rootDirectory)

    def browse_destination(self) -> None:
        """Browse for a new destination directory."""
        self.destDirectory = QFileDialog.getExistingDirectory(self, "Select Destination Folder", str(self.dest))

        if self.destDirectory:
            if self.destCombo.findText(self.destDirectory) == -1:
                self.destCombo.addItem(self.destDirectory)
            self.destCombo.setCurrentIndex(self.destCombo.findText(self.destDirectory))
            self.dest = Path(self.destDirectory)

    def delete_root_item(self) -> None:
        """Delete the current root item from the combo box."""
        if self.rootCombo.count() == 1:
            return
        self.rootCombo.removeItem(self.rootCombo.currentIndex())

    def delete_dest_item(self) -> None:
        """Delete the current destination item from the combo box."""
        if self.destCombo.count() == 1:
            return
        self.destCombo.removeItem(self.destCombo.currentIndex())

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
        self.isRandFiles = self.randomFileG.isChecked()
        self.numberOfFiles = self.numFilesCount.value()

        # Root and Destination
        self.root = Path(self.rootCombo.currentText())
        self.dest = Path(self.destCombo.currentText())

        # Keyword Variables
        if self.incKeysG.isChecked():
            self.keywords = convert_string_to_list(self.incKeysEdit.text())

        if self.excKeysG.isChecked():
            self.notKeywords = convert_string_to_list(self.excKeysEdit.text())

        # Extension Variables
        if self.incExtsG.isChecked():
            self.extensions = convert_string_to_list(self.incExtsEdit.text())

        if self.excExtsG.isChecked():
            self.notExtensions = convert_string_to_list(self.excExtsEdit.text())

        # File Size Variables
        self.isRemoveSizeLimit = not self.sizeButton.isChecked()
        if not self.isRemoveSizeLimit:
            self.minSize = self.sizeLo.value()
            self.maxSize = self.sizeHi.value()
            self.convert_to_bytes()

        # File Length Variables
        self.isRemoveLengthLimit = not self.lengthButton.isChecked()
        if not self.isRemoveLengthLimit:
            self.maxDuration = self.durationHi.value()
            self.minDuration = self.durationLo.value()
            self.convert_minutes_to_seconds()

        # Weight Variables
        if self.weightButton.isChecked():
            self.topWeightValue = self.topWeightSpinBox.value()
            self.bottomWeightValue = self.bottomWeightSpinBox.value()

        # Folder Variables
        self.makeFoldersUnique = self.makeFoldersUniqueCheck.isChecked()
        self.nameOfFolders = self.nameOfFoldersEntry.text()
        self.isCreateFolders = self.folderButton.isChecked()

        # Folder Count
        if self.isCreateFolders:
            self.numFolders = self.numFoldersCount.value()

        # Filename Variables
        if self.fileNameButton.isChecked():
            self.indexFiles = self.indexFilesRadio.isChecked()
            self.renameFiles = self.renameFilesRadio.isChecked()
            self.renameName = self.renameNameEntry.text()

        # Trash Variables
        self.trashEmptyFolders = False
        self.trashSourceFiles = False
        self.trashInvalidFiles = False
        if self.trashButton.isChecked():
            self.trashEmptyFolders = self.isTrashEmpty.isChecked()
            self.trashSourceFiles = self.isTrashSource.isChecked()
            self.trashInvalidFiles = self.isTrashInvalid.isChecked()

        self.startAbsolute = self.root.resolve()
        self.rename2 = " "
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

        self.dest = Path(self.destCombo.currentText())

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
        if self.isRandFiles:
            self.numberOfFiles = random.randint(self.numFilesLo.value(), self.numFilesHi.value())

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
        is_extension = False
        if not self.extensions:
            is_extension = True
        else:
            for extension in self.extensions:
                if re.compile(rf"\.{extension}$", re.IGNORECASE).search(source.suffix) is not None:
                    is_extension = True
                    break
        return is_extension

    def is_keyword(self, source: Path) -> bool:
        """Check if a file contains the specified keywords."""
        is_keyword = False
        if not self.keywords:
            is_keyword = True
        else:
            for keyword in self.keywords:
                if re.compile(rf"(.*){keyword}(.*)", re.IGNORECASE).search(source.stem) is not None:
                    is_keyword = True
                    break
        return is_keyword

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
                    self.rename2 = f"{self.renameName} {file_num + 1}"
                else:
                    x = 1
                    while (dest / f"{self.renameName} {file_num + x}{source.suffix}").exists():
                        x += 1
                    shutil.copy(source_absolute, dest / f"{self.renameName} {file_num + x}{source.suffix}")
                    self.rename2 = f"{self.renameName} {file_num + x}"
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

    def change_stall_time_spinbox(self) -> None:
        """Change the stall time limit based on the spin box value."""
        self.stallLimit = self.stallTimeSpinBox.value()
        self.stallTimeCounter.setText(f"{self.stallLimit}0 s")

    def is_timed_out(self, start_stall_time: float) -> bool:
        """Check if the process has timed out based on stall time."""
        end_stall_time = perf_counter()
        return end_stall_time - start_stall_time > self.stallLimit

    def update_timer(self) -> None:
        """Update the stall time progress bar and counter."""
        self.stallTimeProgressBar.setValue(self.stallTimeProgressBar.value() - 1)
        self.stallTimeCounter.setText(f"{self.stallTimeProgressBar.value() / 100} s")

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

        self.threadpool.globalInstance().start(self.mandala)

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
        self.dest = Path(self.destCombo.currentText())
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

    def switch_file_count(self) -> None:
        """Switch the file count low and high values."""
        if not self.randomFileG.isChecked():
            return

        lo = self.numFilesLo.value()
        hi = self.numFilesHi.value()
        if lo > hi:
            self.numFilesLo.setValue(hi)
            self.numFilesHi.setValue(lo)

    def change_file_label_rand(self) -> None:
        """Change file count group box based on random or count selection."""
        r = self.randomFileG.isChecked()
        self.countFileG.setChecked(not r)

        for child in self.randomFileG.children():
            if isinstance(child, QWidget):
                child.setEnabled(r)

        for child in self.countFileG.children():
            if isinstance(child, QWidget):
                child.setEnabled(not r)

    def change_file_label_count(self) -> None:
        """Change file count group box based on random or count selection."""
        r = self.countFileG.isChecked()
        self.randomFileG.setChecked(not r)

        for child in self.countFileG.children():
            if isinstance(child, QWidget):
                child.setEnabled(r)

        for child in self.randomFileG.children():
            if isinstance(child, QWidget):
                child.setEnabled(not r)

    ### FILE SIZE METHODS ###

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

    def switch_duration(self) -> None:
        """Switch the duration low and high values."""
        lo = self.durationLo.value()
        hi = self.durationHi.value()
        if lo > hi:
            self.durationLo.setValue(hi)
            self.durationHi.setValue(lo)

    def convert_minutes_to_seconds(self) -> None:
        """Convert duration from minutes to seconds if needed."""
        if self.durationType.currentText() == "m":
            self.minDuration = self.durationLo.value() * SECONDS_IN_MINUTE
            self.maxDuration = self.durationHi.value() * SECONDS_IN_MINUTE

    ### KEYWORDS AND EXTENSION METHODS ###

    def switch_keys(self) -> None:
        """Switch the include and exclude keywords."""
        include = self.incKeysEdit.text()
        exclude = self.excKeysEdit.text()
        self.incKeysEdit.setText(exclude)
        self.excKeysEdit.setText(include)

    def switch_extensions(self) -> None:
        """Switch the include and exclude extensions."""
        include = self.incExtsEdit.text()
        exclude = self.excExtsEdit.text()
        self.incExtsEdit.setText(exclude)
        self.excExtsEdit.setText(include)

    ### SETTINGS METHODS ###

    def close_event(self, event: QCloseEvent) -> None:
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
            self.setWindowTitle(f"{name} - Copy Random Files")

    def load_config(self) -> None:
        """Load GUI settings from registry."""
        open_file, _ = QFileDialog.getOpenFileName(self, "Load Configuration", "", ("Configuration (*.ini)"))
        if open_file:
            with Path(open_file).open(encoding="utf-8"):
                settings = QSettings(open_file, QSettings.Format.IniFormat)
                self.restore_gui(settings)
            name = list(settings.fileName().split("/"))[-1][:-4]
            self.setWindowTitle(f"{name} - Copy Random Files")

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
