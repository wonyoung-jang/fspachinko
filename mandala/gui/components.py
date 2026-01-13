"""GUI components in PySide6 for mandala."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, Slot
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
    SizeUnitEnum,
    TimeUnitEnum,
)
from ..utilities.utils import convert_string_to_list

if TYPE_CHECKING:
    from collections.abc import Sequence


class FileCountWidget(QGroupBox):
    """Handles logic for file count settings."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize the file count widget."""
        super().__init__(title, parent, flat=True)

        self.spin_fixed = QSpinBox(minimum=1, maximum=1_000_000_000)
        self.groupbox_fixed = QGroupBox(title="Set Number", flat=True, checkable=True)
        self.groupbox_fixed.toggled.connect(self.update_file_count_fixed)

        fixed_layout = QGridLayout(self.groupbox_fixed)
        fixed_layout.addWidget(QLabel("Count"), 0, 0)
        fixed_layout.addWidget(self.spin_fixed, 0, 1)

        self.spin_min_rand = QSpinBox(minimum=1, maximum=1_000_000_000)
        self.spin_max_rand = QSpinBox(minimum=2, maximum=1_000_000_000)
        self.groupbox_rand = QGroupBox(title="Randomize", flat=True, checkable=True, checked=False)

        self.spin_min_rand.editingFinished.connect(self.validate_rand_file_count)
        self.spin_max_rand.editingFinished.connect(self.validate_rand_file_count)
        self.groupbox_rand.toggled.connect(self.validate_rand_file_count)
        self.groupbox_rand.toggled.connect(self.update_file_count_rand)

        rand_layout = QGridLayout(self.groupbox_rand)
        rand_layout.addWidget(QLabel("Min"), 0, 0)
        rand_layout.addWidget(self.spin_min_rand, 0, 1)
        rand_layout.addWidget(QLabel("Max"), 1, 0)
        rand_layout.addWidget(self.spin_max_rand, 1, 1)

        layout = QGridLayout(self)
        layout.addWidget(self.groupbox_fixed, 0, 0)
        layout.addWidget(self.groupbox_rand, 0, 1)

    @Slot()
    def validate_rand_file_count(self) -> None:
        """Switch the file count low and high values."""
        if self.groupbox_rand.isChecked():
            lo, hi = self.spin_min_rand.value(), self.spin_max_rand.value()
            if lo > hi:
                self.spin_min_rand.setValue(hi)
                self.spin_max_rand.setValue(lo)

    @Slot()
    def update_file_count_rand(self) -> None:
        """Change file count group box based on random or count selection."""
        is_rand = self.groupbox_rand.isChecked()
        self.groupbox_fixed.setChecked(not is_rand)
        self._toggle_group_children(self.groupbox_rand, enabled=is_rand)
        self._toggle_group_children(self.groupbox_fixed, enabled=not is_rand)

    @Slot()
    def update_file_count_fixed(self) -> None:
        """Change file count group box based on random or count selection."""
        is_fixed = self.groupbox_fixed.isChecked()
        self.groupbox_rand.setChecked(not is_fixed)
        self._toggle_group_children(self.groupbox_fixed, enabled=is_fixed)
        self._toggle_group_children(self.groupbox_rand, enabled=not is_fixed)

    def _toggle_group_children(self, groupbox: QGroupBox, *, enabled: bool) -> None:
        """Enable or disable all children of a group box."""
        for child in groupbox.children():
            if isinstance(child, QWidget):
                child.setEnabled(enabled)

    def get_config(self) -> dict:
        """Return clean data for the config."""
        return {
            "num_files": self.spin_fixed.value(),
            "is_rand_file_count": self.groupbox_rand.isChecked(),
            "num_files_rand_min": self.spin_min_rand.value(),
            "num_files_rand_max": self.spin_max_rand.value(),
        }


class FolderCreatorWidget(QGroupBox):
    """Handles logic for creating folders."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize the create folders widget."""
        super().__init__(title, parent, checkable=True, flat=True)

        self.spinbox_folder_count = QSpinBox(minimum=1, maximum=100_000)
        self.lineedit_folder_name = QLineEdit("mandala_output")
        self.chk_unique_folders = QCheckBox("Make Unique")
        self.chk_unique_folders.setChecked(True)
        layout = QGridLayout(self)
        layout.addWidget(QLabel("Count"), 0, 0)
        layout.addWidget(self.spinbox_folder_count, 0, 1)
        layout.addWidget(QLabel("Name"), 1, 0)
        layout.addWidget(self.lineedit_folder_name, 1, 1)
        layout.addWidget(self.chk_unique_folders, 2, 0, 1, 2)

    def get_config(self) -> dict:
        """Return clean data for the config."""
        return {
            "create_folders": self.isChecked(),
            "folder_name": self.lineedit_folder_name.text(),
            "unique_folders": self.chk_unique_folders.isChecked(),
            "num_folders": self.spinbox_folder_count.value() if self.isChecked() else 1,
        }


class FilenameSettingsWidget(QGroupBox):
    """Handles logic for filename settings."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize the filename settings widget."""
        super().__init__(title, parent, checkable=True, flat=True)

        keep_filename = QRadioButton("Keep")
        keep_filename.setChecked(True)
        self.radio_index = QRadioButton("Index")
        self.radio_rename = QRadioButton("Rename")
        self.radio_rename.toggled.connect(lambda: self.lineedit_rename.setEnabled(self.radio_rename.isChecked()))
        self.lineedit_rename = QLineEdit("New Name")
        self.lineedit_rename.setEnabled(False)
        filename_layout = QGridLayout(self)
        filename_layout.addWidget(keep_filename, 0, 0, 1, 2)
        filename_layout.addWidget(self.radio_index, 1, 0, 1, 2)
        filename_layout.addWidget(self.radio_rename, 2, 0)
        filename_layout.addWidget(self.lineedit_rename, 2, 1)

    def get_config(self) -> dict:
        """Return clean data for the config."""
        return {
            "index_files": self.radio_index.isChecked() if self.isChecked() else False,
            "rename_files": self.radio_rename.isChecked() if self.isChecked() else False,
            "rename_name": self.lineedit_rename.text() if self.isChecked() else "",
        }


class TrashSettingsWidget(QGroupBox):
    """Handles logic for trash settings."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize the trash settings widget."""
        super().__init__(title, parent, checkable=True, flat=True)

        self.chk_empty_folders = QCheckBox("Empty Folders")
        self.chk_valid_files = QCheckBox("Valid Files")
        self.chk_invalid_files = QCheckBox("Invalid Files")
        layout = QVBoxLayout(self)
        layout.addWidget(self.chk_empty_folders)
        layout.addWidget(self.chk_valid_files)
        layout.addWidget(self.chk_invalid_files)

    def get_config(self) -> dict:
        """Return clean data for the config."""
        return {
            "trash_empty_folders": self.chk_empty_folders.isChecked() if self.isChecked() else False,
            "trash_source_files": self.chk_valid_files.isChecked() if self.isChecked() else False,
            "trash_invalid_files": self.chk_invalid_files.isChecked() if self.isChecked() else False,
        }


class PathSelectorWidget(QGroupBox):
    """Handles logic for selecting a path."""

    def __init__(self, title: str, items: Sequence[str], parent: QWidget | None = None) -> None:
        """Initialize the path selector widget."""
        super().__init__(title, parent, flat=True)

        self.combo = QComboBox()
        self.combo.addItems(items)

        title = self.title().lower()

        browse_btn = QPushButton("Browse", flat=True)
        browse_btn.setStatusTip(f"Browse for {title} folder")
        browse_btn.clicked.connect(self.browse)

        delete_btn = QPushButton("Delete", flat=True)
        delete_btn.setStatusTip(f"Delete current {title} entry")
        delete_btn.clicked.connect(self.delete_curr_item)

        btn_open = QPushButton("Open", flat=True)
        btn_open.setStatusTip(f"Open current {title} folder in file explorer")
        btn_open.clicked.connect(self.open)

        layout = QHBoxLayout(self)
        layout.addWidget(self.combo, stretch=1)
        layout.addWidget(browse_btn)
        layout.addWidget(delete_btn)
        layout.addWidget(btn_open)

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


class RootPathSelectorWidget(PathSelectorWidget):
    """Handles logic for selecting the root path."""

    def get_config(self) -> dict:
        """Return clean data for the config."""
        root = Path(self.current_path())
        return {
            "root": root.resolve(),
        }


class DestPathSelectorWidget(PathSelectorWidget):
    """Handles logic for selecting the destination path."""

    def get_config(self) -> dict:
        """Return clean data for the config."""
        return {
            "dest": Path(self.current_path()),
        }


class RangeFilterWidget(QGroupBox):
    """Handles logic for ranges (Min/Max), e.g., Weight."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, parent, checkable=True, flat=True)

        self.min_spin = QSpinBox(minimum=0, maximum=1_000_000)
        self.max_spin = QSpinBox(minimum=0, maximum=1_000_000)

        layout = QGridLayout(self)
        layout.addWidget(QLabel("Max per Root Folder"), 0, 0)
        layout.addWidget(self.min_spin, 0, 1)
        layout.addWidget(QLabel("Max per Subfolder"), 1, 0)
        layout.addWidget(self.max_spin, 1, 1)


class WeightFilterWidget(RangeFilterWidget):
    """Handles logic for Weight range (Min/Max)."""

    def get_config(self) -> dict:
        """Return clean data for the config."""
        return {
            "weight_top": self.min_spin.value(),
            "weight_bottom": self.max_spin.value(),
        }


class DblRangeFilterWidget(QGroupBox):
    """Handles logic for ranges (Min/Max), e.g., Size or Duration."""

    def __init__(self, title: str, suffix_options: Sequence[str], parent: QWidget | None = None) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, parent, checkable=True, flat=True)

        self.min_spin = QDoubleSpinBox(minimum=0, maximum=1_000_000)
        self.max_spin = QDoubleSpinBox(minimum=0, maximum=1_000_000)

        # Connect logic internally
        self.min_spin.editingFinished.connect(self.validate_range)
        self.max_spin.editingFinished.connect(self.validate_range)

        self.combo = QComboBox()
        self.combo.addItems(suffix_options)

        layout = QGridLayout(self)
        layout.addWidget(QLabel("Min"), 0, 0)
        layout.addWidget(self.min_spin, 0, 1)
        layout.addWidget(QLabel("Max"), 1, 0)
        layout.addWidget(self.max_spin, 1, 1)
        layout.addWidget(self.combo, 0, 2, 2, 1)

    @Slot()
    def validate_range(self) -> None:
        """Auto-corrects if Min > Max."""
        if self.min_spin.value() > self.max_spin.value():
            min_spin_val = self.min_spin.value()
            self.min_spin.setValue(self.max_spin.value())
            self.max_spin.setValue(min_spin_val)


class FilesizeFilterWidget(DblRangeFilterWidget):
    """Handles logic for Size range (Min/Max)."""

    def get_config(self) -> dict:
        """Return clean data for the config."""
        unit = self.combo.currentText()
        min_size, max_size = self.min_spin.value(), self.max_spin.value()
        if unit == SizeUnitEnum.KB:
            min_size *= BYTES_IN_KILOBYTE
            max_size *= BYTES_IN_KILOBYTE
        elif unit == SizeUnitEnum.MB:
            min_size *= BYTES_IN_MEGABYTE
            max_size *= BYTES_IN_MEGABYTE
        elif unit == SizeUnitEnum.GB:
            min_size *= BYTES_IN_GIGABYTE
            max_size *= BYTES_IN_GIGABYTE
        return {
            "limit_size": self.isChecked(),
            "min_size": min_size,
            "max_size": max_size,
        }


class DurationFilterWidget(DblRangeFilterWidget):
    """Handles logic for Duration range (Min/Max)."""

    def get_config(self) -> dict:
        """Return clean data for the config."""
        unit = self.combo.currentText()
        min_duration, max_duration = self.min_spin.value(), self.max_spin.value()
        if unit == TimeUnitEnum.MINUTES:
            min_duration *= SECONDS_IN_MINUTE
            max_duration *= SECONDS_IN_MINUTE
        return {
            "limit_duration": self.isChecked(),
            "min_duration": min_duration,
            "max_duration": max_duration,
        }


class DualListWidget(QGroupBox):
    """Handles the Include/Exclude pattern for Keywords and Extensions."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize the dual list widget."""
        super().__init__(title, parent, checkable=True, flat=True)

        self.filter_edit = QLineEdit()
        self.filter_include_radio = QRadioButton("Include")
        self.filter_include_radio.setChecked(True)
        self.filter_exclude_radio = QRadioButton("Exclude")
        hbox = QHBoxLayout(self)
        hbox.addWidget(self.filter_edit)
        hbox.addWidget(self.filter_include_radio)
        hbox.addWidget(self.filter_exclude_radio)

        # self.include_edit = QLineEdit()
        # self.exclude_edit = QLineEdit()


        # Sub-groups for visual clarity
        # self.include_groupbox = QGroupBox("Include", checkable=True, flat=True)
        # QHBoxLayout(self.include_groupbox).addWidget(self.include_edit)

        # self.exclude_groupbox = QGroupBox("Exclude", checkable=True, flat=True)
        # QHBoxLayout(self.exclude_groupbox).addWidget(self.exclude_edit)

        # switch_btn = QPushButton("Switch", flat=True)
        # switch_btn.setStatusTip(f"Switch {self.title().lower()} include and exclude filters")
        # switch_btn.clicked.connect(self.switch_text)

        # layout.addWidget(self.include_groupbox, 0, 0)
        # layout.addWidget(self.exclude_groupbox, 1, 0)
        # layout.addWidget(switch_btn, 0, 1, 2, 1)

    @Slot()
    def switch_text(self) -> None:
        """Switch the text between include and exclude."""
        # inc, exc = self.include_edit.text(), self.exclude_edit.text()
        # self.include_edit.setText(exc)
        # self.exclude_edit.setText(inc)


class KeywordsFilterWidget(DualListWidget):
    """Handles the Include/Exclude pattern for Keywords."""

    def get_config(self) -> dict:
        """Return clean data for the config."""
        return {
            "is_keywords": self.isChecked(),
            "is_keywords_include": self.filter_include_radio.isChecked(),
            "is_keywords_exclude": self.filter_exclude_radio.isChecked(),
            "keywords": convert_string_to_list(self.filter_edit.text()),
            # "is_keywords": self.include_groupbox.isChecked(),
            # "is_not_keywords": self.exclude_groupbox.isChecked(),
            # "keywords": convert_string_to_list(self.include_edit.text()) if self.include_groupbox.isChecked() else [],
            # "not_keywords": convert_string_to_list(self.exclude_edit.text())
            # if self.exclude_groupbox.isChecked()
            # else [],
        }


class ExtensionsFilterWidget(DualListWidget):
    """Handles the Include/Exclude pattern for Extensions."""

    def get_config(self) -> dict:
        """Return clean data for the config."""
        return {
            "is_extensions": self.isChecked(),
            "is_extensions_include": self.filter_include_radio.isChecked(),
            "is_extensions_exclude": self.filter_exclude_radio.isChecked(),
            "extensions": convert_string_to_list(self.filter_edit.text()),
            # "is_extensions": self.include_groupbox.isChecked(),
            # "is_not_extensions": self.exclude_groupbox.isChecked(),
            # "extensions": convert_string_to_list(self.include_edit.text())
            # if self.include_groupbox.isChecked() else [],
            # "not_extensions": convert_string_to_list(self.exclude_edit.text())
            # if self.exclude_groupbox.isChecked()
            # else [],
        }


class ExecutionWidget(QWidget):
    """Run/Stop controls, Logs, and Stall Timer."""

    signal_start = Signal()
    signal_stop = Signal()
    signal_close = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the execution widget."""
        super().__init__(parent=parent)

        self.chk_invalid = QCheckBox("Log Invalid")
        self.chk_invalid.setChecked(True)

        self.textbrowser_log = QTextBrowser()
        self.textbrowser_log.setMinimumHeight(175)
        self.textbrowser_log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        self.progbar_stall = QProgressBar(textVisible=False)

        self.dblspin_stall = QDoubleSpinBox(suffix=" s", decimals=1, minimum=1.0, maximum=600_000.0, value=10.0)
        self.dblspin_stall.valueChanged.connect(self.update_stall_display)

        self.label_stall = QLabel("10.0 s")

        self.progbar_main = QProgressBar(value=0, format="%v", textVisible=True, alignment=Qt.AlignmentFlag.AlignCenter)

        self.btn_start = QPushButton("Start", flat=True)
        self.btn_start.setShortcut("Ctrl+R")
        self.btn_start.setStatusTip("Start the file copying process (Ctrl+R)")

        self.btn_stop = QPushButton("Stop", flat=True)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setShortcut("ESC")
        self.btn_stop.setStatusTip("Stop the file copying process (ESC)")

        self.btn_close = QPushButton("Close", flat=True)
        self.btn_close.setShortcut("Ctrl+W")
        self.btn_close.setStatusTip("Close the application (Ctrl+W)")

        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_close.clicked.connect(self.on_close)

        layout = QGridLayout(self)
        layout.addWidget(self.chk_invalid, 0, 0)
        layout.addWidget(self.textbrowser_log, 1, 0, 1, 3)
        layout.addWidget(self.progbar_stall, 2, 0)
        layout.addWidget(self.dblspin_stall, 2, 1)
        layout.addWidget(self.label_stall, 2, 2)
        layout.addWidget(self.progbar_main, 3, 0)
        layout.addWidget(self.btn_start, 4, 0)
        layout.addWidget(self.btn_stop, 4, 1)
        layout.addWidget(self.btn_close, 4, 2)

    @Slot()
    def update_stall_display(self) -> None:
        """Update the stall time label based on spin box value."""
        self.label_stall.setText(f"{self.dblspin_stall.value()} s")

    @Slot()
    def on_start(self) -> None:
        """Handle start button click."""
        self.set_running_state(running=True)
        self.signal_start.emit()

    @Slot()
    def on_stop(self) -> None:
        """Handle stop button click."""
        self.signal_stop.emit()

    @Slot()
    def on_close(self) -> None:
        """Handle close button click."""
        self.signal_close.emit()

    def set_running_state(self, *, running: bool) -> None:
        """Update the GUI based on running state."""
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.label_stall.setEnabled(running)
        self.dblspin_stall.setEnabled(not running)

        if running:
            self.progbar_main.reset()
            self.progbar_stall.setValue(100)
            self.textbrowser_log.clear()

    def log(self, text: str) -> None:
        """Append text to the log viewer."""
        self.textbrowser_log.append(text)

    @Slot()
    def reset_stall_timer_display(self) -> None:
        """Reset the stall timer progress bar."""
        val = self.progbar_stall.maximum()
        self.progbar_stall.setValue(val)
        self.label_stall.setText(f"{val / 100} s")

    @Slot()
    def update_timer(self) -> None:
        """Update the stall time progress bar."""
        val = self.progbar_stall.value()
        self.progbar_stall.setValue(val - 1)
        self.label_stall.setText(f"{val / 100} s")

    def get_config(self) -> dict:
        """Return clean data for the config."""
        return {
            "stall_time_limit": self.dblspin_stall.value(),
            "log_invalid": self.chk_invalid.isChecked(),
        }
