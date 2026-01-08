"""GUI components in PySide6 for mandala."""

from __future__ import annotations

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
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mandala.gui.main_window import QSpinBox

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


class PathSelectorWidget(QGroupBox):
    """Handles logic for selecting a path."""

    def __init__(self, title: str, items: Sequence[str], parent: QWidget | None = None) -> None:
        """Initialize the path selector widget."""
        super().__init__(title, parent, flat=True)

        self.combo = QComboBox()
        self.combo.addItems(items)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_curr_item)

        layout = QHBoxLayout(self)
        layout.addWidget(self.combo, stretch=1)
        layout.addWidget(browse_btn)
        layout.addWidget(delete_btn)

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

    def current_path(self) -> str:
        """Return the currently selected path."""
        return self.combo.currentText()


class RangeFilterWidget(QGroupBox):
    """Handles logic for ranges (Min/Max), e.g., Weight."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, parent, checkable=True, flat=True)

        self.min_spin = QSpinBox(minimum=0, maximum=1_000_000)
        self.max_spin = QSpinBox(minimum=0, maximum=1_000_000)

        layout = QGridLayout(self)
        layout.addWidget(QLabel("Min"), 0, 0)
        layout.addWidget(self.min_spin, 0, 1)
        layout.addWidget(QLabel("Max"), 1, 0)
        layout.addWidget(self.max_spin, 1, 1)


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

    def get_config(self) -> dict:
        """Return clean data for the config."""
        return {
            "enabled": self.isChecked(),
            "min": self.min_spin.value(),
            "max": self.max_spin.value(),
            "unit": self.combo.currentText() if self.combo else None,
        }


class DualListWidget(QGroupBox):
    """Handles the Include/Exclude pattern for Keywords and Extensions."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Initialize the dual list widget."""
        super().__init__(title, parent)
        self.setFlat(True)

        self.include_edit = QLineEdit()
        self.exclude_edit = QLineEdit()

        layout = QGridLayout(self)

        # Sub-groups for visual clarity
        self.include_groupbox = QGroupBox("Include", checkable=True, flat=True)
        QHBoxLayout(self.include_groupbox).addWidget(self.include_edit)

        self.exclude_groupbox = QGroupBox("Exclude", checkable=True, flat=True)
        QHBoxLayout(self.exclude_groupbox).addWidget(self.exclude_edit)

        switch_btn = QPushButton("Switch")
        switch_btn.clicked.connect(self.switch_text)

        layout.addWidget(self.include_groupbox, 0, 0)
        layout.addWidget(self.exclude_groupbox, 1, 0)
        layout.addWidget(switch_btn, 0, 1, 2, 1)

    @Slot()
    def switch_text(self) -> None:
        """Switch the text between include and exclude."""
        inc, exc = self.include_edit.text(), self.exclude_edit.text()
        self.include_edit.setText(exc)
        self.exclude_edit.setText(inc)

    def get_config(self) -> dict:
        """Return the include and exclude lists."""
        return {
            "include": self.include_edit.text(),
            "exclude": self.exclude_edit.text(),
        }


class SidebarWidget(QWidget):
    """Side panel with actions and global settings."""

    save_requested = Signal()
    load_requested = Signal()
    default_requested = Signal()
    reset_requested = Signal()
    root_open_requested = Signal()
    dest_open_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the sidebar widget."""
        super().__init__(parent)

        self.btn_load = QPushButton("Load Config")
        self.btn_save = QPushButton("Save Config")
        self.btn_root = QPushButton("Open Root")
        self.btn_dest = QPushButton("Open Destination")
        self.btn_default = QPushButton("Set Default Config")
        self.btn_reset = QPushButton("Reset to Default Config")

        self.chk_invalid = QCheckBox("Log Invalid")
        self.chk_invalid.setChecked(True)

        # Signals
        self.btn_save.clicked.connect(self.save_requested)
        self.btn_load.clicked.connect(self.load_requested)
        self.btn_default.clicked.connect(self.default_requested)
        self.btn_reset.clicked.connect(self.reset_requested)
        self.btn_root.clicked.connect(self.root_open_requested)
        self.btn_dest.clicked.connect(self.dest_open_requested)

        layout = QVBoxLayout(self)
        layout.addWidget(self.btn_root)
        layout.addWidget(self.btn_dest)
        layout.addSpacing(64)
        layout.addWidget(self.btn_load)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_default)
        layout.addWidget(self.btn_reset)
        layout.addStretch()
        layout.addWidget(self.chk_invalid)


class ExecutionWidget(QWidget):
    """Run/Stop controls, Logs, and Stall Timer."""

    start_requested = Signal()
    stop_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the execution widget."""
        super().__init__(parent)

        self.textbrowser_log = QTextBrowser()
        self.textbrowser_log.setMinimumHeight(175)
        self.textbrowser_log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        self.progbar_stall = QProgressBar(textVisible=False)

        self.dblspin_stall = QDoubleSpinBox(suffix=" s", decimals=1, minimum=1.0, maximum=600_000.0, value=10.0)
        self.dblspin_stall.valueChanged.connect(self.update_stall_display)

        self.label_stall = QLabel("10.0 s")

        self.progbar_main = QProgressBar(value=0, format="%v", textVisible=True, alignment=Qt.AlignmentFlag.AlignCenter)

        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)

        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)

        layout = QGridLayout(self)
        layout.addWidget(self.textbrowser_log, 0, 0, 1, 3)
        layout.addWidget(self.progbar_stall, 1, 0)
        layout.addWidget(self.dblspin_stall, 1, 1)
        layout.addWidget(self.label_stall, 1, 2)
        layout.addWidget(self.progbar_main, 2, 0)
        layout.addWidget(self.btn_start, 2, 1)
        layout.addWidget(self.btn_stop, 2, 2)

    @Slot()
    def update_stall_display(self) -> None:
        """Update the stall time label based on spin box value."""
        self.label_stall.setText(f"{self.dblspin_stall.value()} s")

    def on_start(self) -> None:
        """Handle start button click."""
        self.set_running_state(running=True)
        self.start_requested.emit()

    def on_stop(self) -> None:
        """Handle stop button click."""
        self.stop_requested.emit()

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
