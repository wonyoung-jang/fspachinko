"""GUI components in PySide6 for mandala."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QUrl, Slot
from PySide6.QtGui import QDesktopServices
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
    QMenu,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config.schemas import (
    DiversityModel,
    ExecutionModel,
    FilecountModel,
    FilenameModel,
    FolderModel,
    LimitMinMaxModel,
    ListIncludeExcludeModel,
    TransferModeModel,
)
from ..utils.constants import TransferMode
from ..utils.helpers import convert_string_to_list, get_multiplier
from .qthelpers import init_widget

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PySide6.QtGui import QDragEnterEvent, QDropEvent

logger = logging.getLogger(__name__)


class BaseGroupBox(QGroupBox):
    """Base class for group boxes with common functionality."""

    def __init__(
        self,
        title: str,
        name: str,
        *,
        parent: QWidget | None = None,
        checkable: bool = False,
    ) -> None:
        """Initialize the base group box."""
        super().__init__(title=title, parent=parent)
        init_widget(self, name)
        self.setCheckable(checkable)


class PathSelectorWidget(BaseGroupBox):
    """Handles logic for selecting a path."""

    def __init__(self, title: str, name: str, items: Sequence[str], parent: QWidget | None = None) -> None:
        """Initialize the path selector widget."""
        super().__init__(title, name, parent=parent)
        self.setAcceptDrops(True)

        self.combo = QComboBox()
        init_widget(self.combo, f"{name}_combo")
        self.combo.addItems(items)

        title = self.title().casefold()

        btn_browse = QPushButton("Browse")
        btn_browse.setStatusTip(f"Browse for {title} folder")
        btn_browse.clicked.connect(self.browse)

        btn_delete = QPushButton("Delete")
        btn_delete.setStatusTip(f"Delete current {title} entry")
        btn_delete.clicked.connect(self.delete_curr_item)

        btn_open = QPushButton("Open")
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
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_path()))
        except Exception:
            logger.exception("Failed to open path in file explorer")

    def current_path(self) -> str:
        """Return the currently selected path."""
        return self.combo.currentText()

    def get_config(self) -> Path:
        """Return clean data for the config."""
        return Path(self.combo.currentText()).resolve()


class FileCountWidget(BaseGroupBox):
    """Handles logic for file count settings."""

    def __init__(self, title: str = "File Count", name: str = "filecount", parent: QWidget | None = None) -> None:
        """Initialize the file count widget."""
        super().__init__(title, name, parent=parent)

        self.radio_fixed = QRadioButton("Fixed Count")
        init_widget(self.radio_fixed, f"{name}_fixed_chk")
        self.radio_fixed.setChecked(True)
        self.radio_fixed.toggled.connect(self.toggle_visibility)

        self.radio_rand = QRadioButton("Randomize")
        init_widget(self.radio_rand, f"{name}_rand_chk")
        self.radio_rand.toggled.connect(self.toggle_visibility)

        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.addWidget(self.radio_fixed)
        mode_layout.addWidget(self.radio_rand)

        self.spin_fixed = QSpinBox(minimum=1, maximum=1_000_000_000)
        init_widget(self.spin_fixed, f"{name}_fixed_val")

        self.fixed_widget = QWidget()
        fixed_layout = QFormLayout(self.fixed_widget)
        fixed_layout.addRow("Count", self.spin_fixed)

        self.spin_min_rand = QSpinBox(minimum=1, maximum=1_000_000_000)
        init_widget(self.spin_min_rand, f"{name}_rand_min")
        self.spin_min_rand.valueChanged.connect(self.update_minimum)

        self.spin_max_rand = QSpinBox(minimum=2, maximum=1_000_000_000)
        init_widget(self.spin_max_rand, f"{name}_rand_max")
        self.spin_max_rand.valueChanged.connect(self.update_maximum)

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

    @Slot(int)
    def update_minimum(self, min_val: int) -> None:
        """Update the minimum random file count."""
        self.spin_max_rand.setMinimum(min_val)

    @Slot(int)
    def update_maximum(self, max_val: int) -> None:
        """Update the maximum random file count."""
        self.spin_min_rand.setMaximum(max_val)

    def get_config(self) -> FilecountModel:
        """Return clean data for the config."""
        return FilecountModel(
            count=self.spin_fixed.value(),
            is_rand=self.radio_rand.isChecked(),
            min_rand=self.spin_min_rand.value(),
            max_rand=self.spin_max_rand.value(),
        )


class FolderCreatorWidget(BaseGroupBox):
    """Handles logic for creating folders."""

    def __init__(self, title: str = "Create Folders", name: str = "folder", parent: QWidget | None = None) -> None:
        """Initialize the create folders widget."""
        super().__init__(title, name, parent=parent, checkable=True)

        self.spinbox_folder_count = QSpinBox(minimum=1, maximum=100_000)
        init_widget(self.spinbox_folder_count, f"{name}_count")

        self.lineedit_folder_name = QLineEdit("mandala_output")
        init_widget(self.lineedit_folder_name, f"{name}_name")

        self.chk_unique_folders = QCheckBox("Make Unique")
        init_widget(self.chk_unique_folders, f"{name}_unique")
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


class FilenameWidget(BaseGroupBox):
    """Handles logic for filename template settings."""

    def __init__(self, title: str = "Filename", name: str = "filename", parent: QWidget | None = None) -> None:
        """Initialize the filename template settings widget."""
        super().__init__(title, name, parent=parent)

        self.edit_template = QLineEdit("{original}")
        init_widget(self.edit_template, f"{name}_template")
        self.edit_template.setPlaceholderText("Ex: {original}_{index}")

        self.template_button = QPushButton("Insert Tag")
        self.template_button.setStatusTip("Insert a tag into the template at the cursor position")

        template_menu = QMenu("Tags", self)
        init_widget(template_menu, f"{name}_template_menu")

        self.template_button.setMenu(template_menu)
        for lbl in ("{original}", "{index}", "{date}", "{time}", "{datetime}", "{parent}", "{parentstoroot}"):
            action = template_menu.addAction(lbl)
            action.triggered.connect(lambda _, tag=lbl: self.insert_tag(tag))

        layout = QFormLayout(self)
        layout.addRow("Template:", self.edit_template)
        layout.addRow("Filters", self.template_button)

    @Slot(str)
    def insert_tag(self, tag: str) -> None:
        """Insert a tag into the template at the cursor position."""
        self.edit_template.insert(tag)
        self.edit_template.setFocus()

    def get_config(self) -> FilenameModel:
        """Return clean data for the config."""
        val = self.edit_template.text() or "{original}"
        return FilenameModel(template=val)


class TransferModeWidget(BaseGroupBox):
    """Handles logic for mode settings."""

    def __init__(self, title: str = "Transfer Mode", name: str = "transfermode", parent: QWidget | None = None) -> None:
        """Initialize the mode settings widget."""
        super().__init__(title, name, parent=parent)

        # "Global" trashing option (more of a helpful bonus utility than anything)
        self.chk_trash_empty_folders = QCheckBox("Trash empty folders")
        init_widget(self.chk_trash_empty_folders, f"{name}_trash_empty_folders")

        # Actual transfer mode options
        self.combo_mode = QComboBox()
        init_widget(self.combo_mode, f"{name}_mode")
        self.combo_mode.addItems(list(TransferMode))

        layout = QFormLayout(self)
        layout.addRow(self.chk_trash_empty_folders)
        layout.addRow("Mode:", self.combo_mode)

    def get_config(self) -> TransferModeModel:
        """Return clean data for the config."""
        return TransferModeModel(
            trash_empty_folder=self.chk_trash_empty_folders.isChecked(),
            transfer_mode=TransferMode(self.combo_mode.currentText()),
        )


class DualListFilterWidget(BaseGroupBox):
    """Handles the Include/Exclude pattern for Keywords and Extensions."""

    def __init__(self, title: str, name: str, parent: QWidget | None = None) -> None:
        """Initialize the dual list widget."""
        super().__init__(title, name, parent=parent)

        self.filter_edit = QLineEdit()
        init_widget(self.filter_edit, f"{name}_text")

        self.filter_include_radio = QRadioButton("Include")
        init_widget(self.filter_include_radio, f"{name}_include")
        self.filter_include_radio.setChecked(True)

        self.filter_exclude_radio = QRadioButton("Exclude")
        init_widget(self.filter_exclude_radio, f"{name}_exclude")

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
        super().__init__(title, name, parent=parent, checkable=True)

        self.mapping = mapping

        self.min_spin = QDoubleSpinBox(self, minimum=0, maximum=1_000_000)
        init_widget(self.min_spin, f"{name}_minimum")
        self.min_spin.valueChanged.connect(self.update_minimum)

        self.max_spin = QDoubleSpinBox(self, minimum=0, maximum=1_000_000)
        init_widget(self.max_spin, f"{name}_maximum")
        self.max_spin.valueChanged.connect(self.update_maximum)

        self.combo = QComboBox(self)
        init_widget(self.combo, f"{name}_unit")
        self.combo.addItems(suffix_options)

        layout = QFormLayout(self)
        layout.addRow("Min", self.min_spin)
        layout.addRow("Max", self.max_spin)
        layout.addRow(self.combo)

    @Slot(int)
    def update_minimum(self, min_val: int) -> None:
        """Update the minimum random file count."""
        self.max_spin.setMinimum(min_val)

    @Slot(int)
    def update_maximum(self, max_val: int) -> None:
        """Update the maximum random file count."""
        self.min_spin.setMaximum(max_val)

    def get_config(self) -> LimitMinMaxModel:
        """Return clean data for the config."""
        mult = get_multiplier(self.combo.currentText(), self.mapping)
        minimum, maximum = self.min_spin.value() * mult, self.max_spin.value() * mult
        return LimitMinMaxModel(limit=self.isChecked(), minimum=minimum, maximum=maximum)


class DiversityFilterWidget(BaseGroupBox):
    """Handles logic for diversity range (root/leaf)."""

    def __init__(self, title: str = "Diversity", name: str = "diversity", parent: QWidget | None = None) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, name, parent=parent)

        self.spin_max_per_folder = QSpinBox(minimum=0, maximum=1_000_000)
        init_widget(self.spin_max_per_folder, f"{name}_max_per_folder")

        layout = QFormLayout(self)
        layout.addRow("Max files per folder", self.spin_max_per_folder)

    def get_config(self) -> DiversityModel:
        """Return clean data for the config."""
        return DiversityModel(max_per_folder=self.spin_max_per_folder.value())


class ProgressWidget(QWidget):
    """Progress bars and execution controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the execution widget."""
        super().__init__(parent=parent)

        self.progbar_total = QProgressBar(value=0, textVisible=True)
        self.progbar_total.setStatusTip("Total progress bar, max is set at number of output folders")

        self.progbar_folder = QProgressBar(value=0, textVisible=True)
        self.progbar_folder.setStatusTip("Current folder progress bar, max is set at number of files to copy")

        prog_form_layout = QFormLayout(self)
        prog_form_layout.addRow("Total:", self.progbar_total)
        prog_form_layout.addRow("Folder:", self.progbar_folder)

    @Slot()
    def update_total_prog(self) -> None:
        """Update the total progress bar."""
        self.progbar_total.setValue(self.progbar_total.value() + 1)


class ExecutionWidget(QWidget):
    """Logging and execution widget."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the execution widget."""
        super().__init__(parent=parent)

        # Log
        self.textbrowser_log = QTextBrowser()
        init_widget(self.textbrowser_log, "execution_log")
        self.textbrowser_log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.textbrowser_log.setStatusTip("Log for output messages")

        # Dry Run
        self.chk_dry_run = QCheckBox("Dry Run")
        init_widget(self.chk_dry_run, "execution_dry_run")
        self.chk_dry_run.setStatusTip("If checked, no files will actually be copied.")

        layout = QGridLayout(self)
        layout.addWidget(self.chk_dry_run, 0, 0)
        layout.addWidget(self.textbrowser_log, 1, 0)

    def get_config(self) -> ExecutionModel:
        """Return clean data for the config."""
        return ExecutionModel(
            dry_run=self.chk_dry_run.isChecked(),
        )
