"""GUI components in PySide6 for mandala."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
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

from mandala.utils.helpers import get_multiplier

from ..config.schemas import (
    DiversityModel,
    ExecutionModel,
    FilecountModel,
    FilenameModel,
    FolderModel,
    LimitMinMaxModel,
    ListIncludeExcludeModel,
    ProgressModel,
    TrashModel,
)
from ..utils.helpers import convert_string_to_list

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PySide6.QtGui import QDragEnterEvent, QDropEvent


class BaseGroupBox(QGroupBox):
    """Base class for group boxes with common functionality."""

    def __init__(
        self,
        title: str,
        name: str,
        *,
        parent: QWidget | None = None,
        checkable: bool = False,
        flat: bool = False,
    ) -> None:
        """Initialize the base group box."""
        super().__init__(title=title, parent=parent)
        self.setObjectName(name)
        self.setCheckable(checkable)
        self.setFlat(flat)


class PathSelectorWidget(BaseGroupBox):
    """Handles logic for selecting a path."""

    def __init__(self, title: str, name: str, items: Sequence[str], parent: QWidget | None = None) -> None:
        """Initialize the path selector widget."""
        super().__init__(title, name, parent=parent, checkable=False, flat=True)
        self.setAcceptDrops(True)

        self.combo = QComboBox()
        self.combo.addItems(items)
        self.combo.setObjectName(f"{name}_combo")

        title = self.title().casefold()

        btn_browse = QPushButton("Browse", flat=True)
        btn_browse.setStatusTip(f"Browse for {title} folder")
        btn_browse.clicked.connect(self.browse)

        btn_delete = QPushButton("Delete", flat=True)
        btn_delete.setStatusTip(f"Delete current {title} entry")
        btn_delete.clicked.connect(self.delete_curr_item)

        btn_open = QPushButton("Open", flat=True)
        btn_open.setStatusTip(f"Open current {title} folder in file explorer")
        btn_open.clicked.connect(self.open)

        layout = QHBoxLayout(self)
        layout.addWidget(self.combo, stretch=1)
        layout.addWidget(btn_browse)
        layout.addWidget(btn_delete)
        layout.addWidget(btn_open)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        """Handle drag enter event for folder paths."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """Handle drop event for folder paths."""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).is_dir():
                if self.combo.findText(path) == -1:
                    self.combo.addItem(path)
                self.combo.setCurrentText(path)

    @Slot()
    def browse(self) -> None:
        """Return the browse button."""
        d = QFileDialog.getExistingDirectory(self, f"Select {self.title()}")
        if d:
            if self.combo.findText(d) == -1:
                self.combo.addItem(d)
            self.combo.setCurrentText(d)

    @Slot()
    def delete_curr_item(self) -> None:
        """Delete the currently selected item."""
        if self.combo.count() > 1:
            self.combo.removeItem(self.combo.currentIndex())

    @Slot()
    def open(self) -> None:
        """Open the currently selected path in file explorer."""
        os.startfile(self.current_path())

    def current_path(self) -> str:
        """Return the currently selected path."""
        return self.combo.currentText()

    def get_config(self) -> Path:
        """Return clean data for the config."""
        return Path(self.combo.currentText()).resolve()


class FileCountWidget(BaseGroupBox):
    """Handles logic for file count settings."""

    def __init__(self, title: str, name: str, parent: QWidget | None = None) -> None:
        """Initialize the file count widget."""
        super().__init__(title, name, parent=parent, checkable=False, flat=True)

        self.radio_fixed = QRadioButton("Fixed Count")
        self.radio_fixed.setChecked(True)
        self.radio_fixed.setObjectName(f"{name}_fixed_chk")
        self.radio_fixed.toggled.connect(self.toggle_visibility)

        self.radio_rand = QRadioButton("Randomize")
        self.radio_rand.setObjectName(f"{name}_rand_chk")
        self.radio_rand.toggled.connect(self.toggle_visibility)

        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.addWidget(self.radio_fixed)
        mode_layout.addWidget(self.radio_rand)

        self.spin_fixed = QSpinBox(minimum=1, maximum=1_000_000_000)
        self.spin_fixed.setObjectName(f"{name}_fixed_val")

        self.fixed_widget = QWidget()
        fixed_layout = QFormLayout(self.fixed_widget)
        fixed_layout.addRow("Count", self.spin_fixed)

        self.spin_min_rand = QSpinBox(minimum=1, maximum=1_000_000_000)
        self.spin_min_rand.setObjectName(f"{name}_rand_min")
        self.spin_min_rand.editingFinished.connect(self.validate_rand_file_count)

        self.spin_max_rand = QSpinBox(minimum=2, maximum=1_000_000_000)
        self.spin_max_rand.setObjectName(f"{name}_rand_max")
        self.spin_max_rand.editingFinished.connect(self.validate_rand_file_count)

        self.rand_widget = QWidget()
        self.rand_widget.setVisible(False)
        rand_layout = QFormLayout(self.rand_widget)
        rand_layout.addRow("Min", self.spin_min_rand)
        rand_layout.addRow("Max", self.spin_max_rand)

        layout = QVBoxLayout(self)
        layout.addWidget(mode_widget)
        layout.addWidget(self.fixed_widget)
        layout.addWidget(self.rand_widget)

    @Slot()
    def toggle_visibility(self) -> None:
        """Toggle visibility of random/fixed widgets."""
        is_rand = self.radio_rand.isChecked()
        self.rand_widget.setVisible(is_rand)
        self.fixed_widget.setVisible(not is_rand)

    @Slot()
    def validate_rand_file_count(self) -> None:
        """Switch the file count low and high values."""
        lo, hi = self.spin_min_rand.value(), self.spin_max_rand.value()
        if lo > hi:
            self.spin_min_rand.setValue(hi)
            self.spin_max_rand.setValue(lo)

    def get_config(self) -> FilecountModel:
        """Return clean data for the config."""
        return FilecountModel(
            count=self.spin_fixed.value(),
            is_rand_count=self.radio_rand.isChecked(),
            count_min_rand=self.spin_min_rand.value(),
            count_max_rand=self.spin_max_rand.value(),
        )


class FolderCreatorWidget(BaseGroupBox):
    """Handles logic for creating folders."""

    def __init__(self, title: str, name: str, parent: QWidget | None = None) -> None:
        """Initialize the create folders widget."""
        super().__init__(title, name, parent=parent, checkable=True, flat=True)

        self.spinbox_folder_count = QSpinBox(minimum=1, maximum=100_000)
        self.spinbox_folder_count.setObjectName(f"{name}_count")

        self.lineedit_folder_name = QLineEdit("mandala_output")
        self.lineedit_folder_name.setObjectName(f"{name}_name")

        self.chk_unique_folders = QCheckBox("Make Unique")
        self.chk_unique_folders.setObjectName(f"{name}_unique")
        self.chk_unique_folders.setChecked(True)

        layout = QFormLayout(self)
        layout.addRow("Count", self.spinbox_folder_count)
        layout.addRow("Name", self.lineedit_folder_name)
        layout.addRow(self.chk_unique_folders)

    def get_config(self) -> FolderModel:
        """Return clean data for the config."""
        return FolderModel(
            create=self.isChecked(),
            unique=self.chk_unique_folders.isChecked(),
            name=self.lineedit_folder_name.text(),
            count=self.spinbox_folder_count.value() if self.isChecked() else 1,
        )


class FilenameSettingsWidget(BaseGroupBox):
    """Handles logic for filename settings."""

    def __init__(self, title: str, name: str, parent: QWidget | None = None) -> None:
        """Initialize the filename settings widget."""
        super().__init__(title, name, parent=parent, flat=True)

        keep_filename = QRadioButton("Keep")
        keep_filename.setChecked(True)

        self.radio_index = QRadioButton("Index")
        self.radio_index.setObjectName(f"{name}_index")

        self.radio_rename = QRadioButton("Rename")
        self.radio_rename.setObjectName(f"{name}_rename")
        self.radio_rename.toggled.connect(lambda: self.lineedit_rename.setEnabled(self.radio_rename.isChecked()))

        self.lineedit_rename = QLineEdit("New Name")
        self.lineedit_rename.setObjectName(f"{name}_text")
        self.lineedit_rename.setEnabled(False)

        layout = QFormLayout(self)
        layout.addRow(keep_filename)
        layout.addRow(self.radio_index)
        layout.addRow(self.radio_rename, self.lineedit_rename)

    def get_config(self) -> FilenameModel:
        """Return clean data for the config."""
        return FilenameModel(
            is_index=self.radio_index.isChecked(),
            is_rename=self.radio_rename.isChecked(),
            rename_to=self.lineedit_rename.text(),
        )


class TrashSettingsWidget(BaseGroupBox):
    """Handles logic for trash settings."""

    def __init__(self, title: str, name: str, parent: QWidget | None = None) -> None:
        """Initialize the trash settings widget."""
        super().__init__(title, name, parent=parent, checkable=True, flat=True)

        self.chk_empty_folders = QCheckBox("Empty Folders")
        self.chk_empty_folders.setObjectName(f"{name}_empty_folders")

        self.chk_valid_files = QCheckBox("Valid Files")
        self.chk_valid_files.setObjectName(f"{name}_valid_files")

        self.chk_invalid_files = QCheckBox("Invalid Files")
        self.chk_invalid_files.setObjectName(f"{name}_invalid_files")

        layout = QFormLayout(self)
        layout.addRow(self.chk_empty_folders)
        layout.addRow(self.chk_valid_files)
        layout.addRow(self.chk_invalid_files)

    def get_config(self) -> TrashModel:
        """Return clean data for the config."""
        if not self.isChecked():
            return TrashModel(empty_folder=False, source_file=False, invalid_file=False)
        return TrashModel(
            empty_folder=self.chk_empty_folders.isChecked(),
            source_file=self.chk_valid_files.isChecked(),
            invalid_file=self.chk_invalid_files.isChecked(),
        )


class DualListFilterWidget(BaseGroupBox):
    """Handles the Include/Exclude pattern for Keywords and Extensions."""

    def __init__(self, title: str, name: str, parent: QWidget | None = None) -> None:
        """Initialize the dual list widget."""
        super().__init__(title, name, parent=parent, flat=True)

        self.filter_edit = QLineEdit()
        self.filter_edit.setObjectName(f"{name}_text")

        self.filter_include_radio = QRadioButton("Include")
        self.filter_include_radio.setChecked(True)
        self.filter_include_radio.setObjectName(f"{name}_include")

        self.filter_exclude_radio = QRadioButton("Exclude")
        self.filter_exclude_radio.setObjectName(f"{name}_exclude")

        hbox = QHBoxLayout(self)
        hbox.addWidget(self.filter_edit)
        hbox.addWidget(self.filter_include_radio)
        hbox.addWidget(self.filter_exclude_radio)

    def get_config(self) -> ListIncludeExcludeModel:
        """Return clean data for the config."""
        return ListIncludeExcludeModel(
            include=self.filter_include_radio.isChecked(),
            exclude=self.filter_exclude_radio.isChecked(),
            text=convert_string_to_list(self.filter_edit.text()),
        )


class DblRangeFilterWidget(BaseGroupBox):
    """Handles logic for ranges (Min/Max), e.g., Size or Duration."""

    def __init__(
        self,
        title: str,
        name: str,
        suffix_options: Sequence[str],
        mapping: dict[str, int],
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, name, parent=parent, checkable=True, flat=True)

        self.mapping = mapping

        self.min_spin = QDoubleSpinBox(minimum=0, maximum=1_000_000)
        self.min_spin.setObjectName(f"{name}_min")
        self.min_spin.valueChanged.connect(self.validate_range)

        self.max_spin = QDoubleSpinBox(minimum=0, maximum=1_000_000)
        self.max_spin.setObjectName(f"{name}_max")
        self.max_spin.valueChanged.connect(self.validate_range)

        self.combo = QComboBox()
        self.combo.addItems(suffix_options)
        self.combo.setObjectName(f"{name}_unit")

        layout = QFormLayout(self)
        layout.addRow("Min", self.min_spin)
        layout.addRow("Max", self.max_spin)
        layout.addRow(self.combo)

    @Slot()
    def validate_range(self) -> None:
        """Auto-corrects if Min > Max."""
        lo, hi = self.min_spin.value(), self.max_spin.value()
        if lo > hi:
            self.min_spin.setValue(hi)
            self.max_spin.setValue(lo)

    def get_config(self) -> LimitMinMaxModel:
        """Return clean data for the config."""
        mult = get_multiplier(self.combo.currentText(), self.mapping)
        minimum, maximum = self.min_spin.value() * mult, self.max_spin.value() * mult
        return LimitMinMaxModel(limit=self.isChecked(), minimum=minimum, maximum=maximum)


class RangeFilterWidget(BaseGroupBox):
    """Handles logic for ranges (Min/Max), e.g., Weight."""

    def __init__(self, title: str, name: str, parent: QWidget | None = None) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, name, parent=parent, checkable=True, flat=True)

        self.min_spin = QSpinBox(minimum=0, maximum=1_000_000)
        self.min_spin.setObjectName(f"{name}_min")

        self.max_spin = QSpinBox(minimum=0, maximum=1_000_000)
        self.max_spin.setObjectName(f"{name}_max")

        layout = QFormLayout(self)
        layout.addRow("Max per Root Folder", self.min_spin)
        layout.addRow("Max per Subfolder", self.max_spin)


class DiversityFilterWidget(RangeFilterWidget):
    """Handles logic for diversity range (root/leaf)."""

    def get_config(self) -> DiversityModel:
        """Return clean data for the config."""
        if not self.isChecked():
            return DiversityModel(root_limit=0, leaf_limit=0)
        return DiversityModel(
            root_limit=self.min_spin.value(),
            leaf_limit=self.max_spin.value(),
        )


class ProgressWidget(QWidget):
    """Progress bars and execution controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the execution widget."""
        super().__init__(parent=parent)

        self.progbar_total = QProgressBar(value=0, textVisible=True)
        self.progbar_total.setStatusTip("Total progress bar, max is set at number of output folders")

        self.progbar_folder = QProgressBar(value=0, textVisible=True)
        self.progbar_folder.setStatusTip("Current folder progress bar, max is set at number of files to copy")

        self.progbar_stall = QProgressBar(value=0, textVisible=True)
        self.progbar_stall.setStatusTip("Stall time progress bar, counts down from stall time limit per file")

        self.dblspin_stall = QDoubleSpinBox(suffix=" s", decimals=1, minimum=1.0, maximum=600_000.0, value=10.0)
        self.dblspin_stall.setObjectName("progress_stall_time_limit")
        self.dblspin_stall.setStatusTip("Set the stall time limit for finding a valid file in seconds")

        prog_form_layout = QFormLayout(self)
        prog_form_layout.addRow("Total:", self.progbar_total)
        prog_form_layout.addRow("Folder:", self.progbar_folder)
        prog_form_layout.addRow("Stall:", self.progbar_stall)
        prog_form_layout.addRow("Stall Time:", self.dblspin_stall)

    @Slot()
    def reset_stall_prog(self) -> None:
        """Reset the stall timer progress bar."""
        self.progbar_stall.setValue(self.progbar_stall.maximum())

    @Slot()
    def update_stall_prog(self) -> None:
        """Update the stall time progress bar."""
        self.progbar_stall.setValue(self.progbar_stall.value() - 1)

    @Slot()
    def update_total_prog(self) -> None:
        """Update the total progress bar."""
        self.progbar_total.setValue(self.progbar_total.value() + 1)

    def get_config(self) -> ProgressModel:
        """Return clean data for the config."""
        return ProgressModel(
            stall_time_limit=self.dblspin_stall.value(),
        )


class ExecutionWidget(QWidget):
    """Run/Stop controls, Logs, and Stall Timer."""

    start = Signal()
    stop = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the execution widget."""
        super().__init__(parent=parent)

        # Log
        self.chk_log_invalid = QCheckBox("Log Invalid")
        self.chk_log_invalid.setObjectName("execution_log_invalid")
        self.chk_log_invalid.setStatusTip("If checked, invalid files will be logged in the output log.")

        self.textbrowser_log = QTextBrowser()
        self.textbrowser_log.setFont("Consolas")
        self.textbrowser_log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.textbrowser_log.setStatusTip("Log for output messages")

        # Dry Run
        self.chk_dry_run = QCheckBox("Dry Run")
        self.chk_dry_run.setObjectName("execution_dry_run")
        self.chk_dry_run.setStatusTip("If checked, no files will actually be copied.")

        # Controls
        self.btn_start = QPushButton("Start", flat=True)
        self.btn_start.setShortcut("Ctrl+R")
        self.btn_start.setStatusTip("Start the file copying process (Ctrl+R)")
        self.btn_start.clicked.connect(self.start.emit)

        self.btn_stop = QPushButton("Stop", flat=True)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setShortcut("ESC")
        self.btn_stop.setStatusTip("Stop the file copying process (ESC)")
        self.btn_stop.clicked.connect(self.stop.emit)

        layout = QGridLayout(self)
        layout.addWidget(self.textbrowser_log, 0, 0, 1, 4)
        layout.addWidget(self.chk_log_invalid, 1, 0)
        layout.addWidget(self.chk_dry_run, 1, 1)
        layout.addWidget(self.btn_start, 1, 2)
        layout.addWidget(self.btn_stop, 1, 3)

    def get_config(self) -> ExecutionModel:
        """Return clean data for the config."""
        return ExecutionModel(
            log_invalid=self.chk_log_invalid.isChecked(),
            dry_run=self.chk_dry_run.isChecked(),
        )
