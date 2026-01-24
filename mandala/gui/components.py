"""GUI components in PySide6 for mandala."""

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

from ..config import (
    DiversityModel,
    FilecountModel,
    FilenameModel,
    FolderModel,
    LimitMinMaxModel,
    ListIncludeExcludeModel,
    TransferModeModel,
    WalkerModel,
)
from ..core import get_available_transfer_modes
from ..utils import ByteUnit, FilenameTemplate, TimeUnit, TransferMode, convert_string_to_list
from .qthelpers import init_widget, set_widget_tips

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
        self.setFlat(True)


class PathSelectorWidget(BaseGroupBox):
    """Handles logic for selecting a path."""

    def __init__(self, title: str, name: str, items: Sequence[str], parent: QWidget | None = None) -> None:
        """Initialize the path selector widget."""
        super().__init__(title, name, parent=parent)
        self.setAcceptDrops(True)

        title = self.title().casefold()

        self.combo = QComboBox()
        self.combo.addItems(items)
        init_widget(self.combo, f"{name}_combo")
        set_widget_tips(self.combo, f"Select or enter a path for {title}.")

        self.btn_browse = QPushButton("Browse")
        self.btn_browse.clicked.connect(self.browse)
        init_widget(self.btn_browse, f"{name}_browse_btn")
        set_widget_tips(self.btn_browse, f"Browse for {title} folder.")

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_curr_item)
        init_widget(self.btn_delete, f"{name}_delete_btn")
        set_widget_tips(self.btn_delete, f"Delete current {title} entry.")

        self.btn_open = QPushButton("Open")
        self.btn_open.clicked.connect(self.open)
        init_widget(self.btn_open, f"{name}_open_btn")
        set_widget_tips(self.btn_open, f"Open current {title} folder in file explorer.")

        layout = QHBoxLayout(self)
        layout.addWidget(self.combo, stretch=1)
        layout.addWidget(self.btn_browse)
        layout.addWidget(self.btn_delete)
        layout.addWidget(self.btn_open)

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
        return Path(self.current_path()).resolve()


class FileCountWidget(BaseGroupBox):
    """Handles logic for file count settings."""

    def __init__(self, title: str = "File Count", name: str = "filecount", parent: QWidget | None = None) -> None:
        """Initialize the file count widget."""
        super().__init__(title, name, parent=parent)

        self.radio_fixed = QRadioButton("Fixed Count")
        self.radio_fixed.setChecked(True)
        init_widget(self.radio_fixed, f"{name}_fixed_chk")
        set_widget_tips(self.radio_fixed, "Select fixed file count.")

        self.radio_rand = QRadioButton("Randomize")
        init_widget(self.radio_rand, f"{name}_rand_chk")
        set_widget_tips(self.radio_rand, "Select random file count.")

        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.addWidget(self.radio_fixed)
        mode_layout.addWidget(self.radio_rand)

        self.spin_fixed = QSpinBox(minimum=1, maximum=1_000_000_000)
        init_widget(self.spin_fixed, f"{name}_fixed_val")
        set_widget_tips(self.spin_fixed, "Number of files to copy.")

        self.fixed_widget = QWidget()
        init_widget(self.fixed_widget, f"{name}_fixed_widget")
        set_widget_tips(self.fixed_widget, "Fixed file count settings.")

        fixed_layout = QFormLayout(self.fixed_widget)
        fixed_layout.addRow("Count", self.spin_fixed)

        self.spin_min_rand = QSpinBox(minimum=1, maximum=1_000_000_000)
        init_widget(self.spin_min_rand, f"{name}_rand_min")
        set_widget_tips(self.spin_min_rand, "Minimum random file count.")

        self.spin_max_rand = QSpinBox(minimum=2, maximum=1_000_000_000)
        init_widget(self.spin_max_rand, f"{name}_rand_max")
        set_widget_tips(self.spin_max_rand, "Maximum random file count.")

        self.spin_min_rand.valueChanged.connect(self.spin_max_rand.setMinimum)
        self.spin_max_rand.valueChanged.connect(self.spin_min_rand.setMaximum)

        self.rand_widget = QWidget()
        self.rand_widget.setVisible(False)
        init_widget(self.rand_widget, f"{name}_rand_widget")
        set_widget_tips(self.rand_widget, "Random file count settings.")

        self.radio_fixed.toggled.connect(self.fixed_widget.setVisible)
        self.radio_rand.toggled.connect(self.rand_widget.setVisible)

        rand_layout = QFormLayout(self.rand_widget)
        rand_layout.addRow("Min", self.spin_min_rand)
        rand_layout.addRow("Max", self.spin_max_rand)

        layout = QVBoxLayout(self)
        layout.addWidget(mode_widget)
        layout.addWidget(self.fixed_widget)
        layout.addWidget(self.rand_widget)

    def get_config(self) -> FilecountModel:
        """Return clean data for the config."""
        return FilecountModel(
            count=self.spin_fixed.value(),
            rand_enabled=self.radio_rand.isChecked(),
            rand_min=self.spin_min_rand.value(),
            rand_max=self.spin_max_rand.value(),
        )


class FolderCreatorWidget(BaseGroupBox):
    """Handles logic for creating folders."""

    def __init__(self, title: str = "Create Folders", name: str = "folder", parent: QWidget | None = None) -> None:
        """Initialize the create folders widget."""
        super().__init__(title, name, parent=parent, checkable=True)

        self.spinbox_folder_count = QSpinBox(minimum=1, maximum=100_000)
        init_widget(self.spinbox_folder_count, f"{name}_count")
        set_widget_tips(self.spinbox_folder_count, "Number of folders to create.")

        self.lineedit_folder_name = QLineEdit()
        self.lineedit_folder_name.setPlaceholderText("Ex: Random_Files")
        init_widget(self.lineedit_folder_name, f"{name}_name")
        set_widget_tips(self.lineedit_folder_name, "Template for naming created folders.")

        self.chk_unique_folders = QCheckBox("Make Unique")
        self.chk_unique_folders.setChecked(True)
        init_widget(self.chk_unique_folders, f"{name}_unique")
        set_widget_tips(
            self.chk_unique_folders,
            "If checked, created folder names will have a unique suffix to avoid name collisions.",
        )

        layout = QFormLayout(self)
        layout.addRow("Count", self.spinbox_folder_count)
        layout.addRow("Name", self.lineedit_folder_name)
        layout.addRow(self.chk_unique_folders)

    def get_config(self) -> FolderModel:
        """Return clean data for the config."""
        return FolderModel(
            create_enabled=self.isChecked(),
            unique_enabled=self.chk_unique_folders.isChecked(),
            name=self.lineedit_folder_name.text(),
            count=self.spinbox_folder_count.value() if self.isChecked() else 1,
        )


class FilenameWidget(BaseGroupBox):
    """Handles logic for filename template settings."""

    def __init__(self, title: str = "Filename", name: str = "filename", parent: QWidget | None = None) -> None:
        """Initialize the filename template settings widget."""
        super().__init__(title, name, parent=parent)

        self.edit_template = QLineEdit("{original}", placeholderText="Ex: {original}_{index}")
        init_widget(self.edit_template, f"{name}_template")
        set_widget_tips(
            self.edit_template,
            "Template for renaming files. Use the 'Insert Tag' button to add tags.",
        )

        self.btn_template = QPushButton("Insert Tag")
        init_widget(self.btn_template, f"{name}_template_button")
        set_widget_tips(self.btn_template, "Insert a tag into the template at the cursor position.")

        self.menu_template = QMenu("Tags", self)
        init_widget(self.menu_template, f"{name}_template_menu")
        set_widget_tips(self.menu_template, "Select a tag to insert into the filename template.")

        self.btn_template.setMenu(self.menu_template)
        init_widget(self.btn_template, f"{name}_template_button")
        set_widget_tips(self.btn_template, "Insert a tag into the template at the cursor position.")

        for lbl in FilenameTemplate:
            action = self.menu_template.addAction(lbl)
            action.triggered.connect(lambda _, tag=lbl: self.insert_tag(tag))

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(lambda: self.edit_template.clear())
        init_widget(self.btn_clear, f"{name}_clear_button")
        set_widget_tips(self.btn_clear, "Clear the filename template.")

        layout = QFormLayout(self)
        layout.addRow("Template:", self.edit_template)
        layout.addRow("Filters", self.btn_template)
        layout.addRow(self.btn_clear)

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

        self.combo_mode = QComboBox()
        available_modes = get_available_transfer_modes()
        self.combo_mode.addItems(available_modes)
        init_widget(self.combo_mode, f"{name}_mode")
        set_widget_tips(self.combo_mode, "Select the transfer mode to use.")

        self.chk_dry_run = QCheckBox("Dry Run")
        init_widget(self.chk_dry_run, f"{name}_dry_run")
        set_widget_tips(self.chk_dry_run, "If checked, no files will actually be copied.")

        layout = QFormLayout(self)
        layout.addRow("Mode:", self.combo_mode)
        layout.addRow(self.chk_dry_run)

    def get_config(self) -> TransferModeModel:
        """Return clean data for the config."""
        return TransferModeModel(
            transfer_mode=TransferMode(self.combo_mode.currentText()),
            dry_run_enabled=self.chk_dry_run.isChecked(),
        )


class DualListFilterWidget(BaseGroupBox):
    """Handles the Include/Exclude pattern for Keywords and Extensions."""

    def __init__(self, title: str, name: str, parent: QWidget | None = None) -> None:
        """Initialize the dual list widget."""
        super().__init__(title, name, parent=parent)

        self.filter_edit = QLineEdit()
        init_widget(self.filter_edit, f"{name}_text")
        set_widget_tips(self.filter_edit, f"Enter {title.lower()} separated by commas.")

        self.filter_include_radio = QRadioButton("Include")
        self.filter_include_radio.setChecked(True)
        init_widget(self.filter_include_radio, f"{name}_include")
        set_widget_tips(self.filter_include_radio, f"Include only items matching the {title.lower()} filter.")

        self.filter_exclude_radio = QRadioButton("Exclude")
        init_widget(self.filter_exclude_radio, f"{name}_exclude")
        set_widget_tips(self.filter_exclude_radio, f"Exclude items matching the {title.lower()} filter.")

        layout = QHBoxLayout(self)
        layout.addWidget(self.filter_edit)
        layout.addWidget(self.filter_include_radio)
        layout.addWidget(self.filter_exclude_radio)

    def get_config(self) -> ListIncludeExcludeModel:
        """Return clean data for the config."""
        return ListIncludeExcludeModel(
            include_enabled=self.filter_include_radio.isChecked(),
            exclude_enabled=self.filter_exclude_radio.isChecked(),
            text=convert_string_to_list(self.filter_edit.text()),
        )


class DblRangeFilterWidget(BaseGroupBox):
    """Handles logic for ranges (Min/Max), e.g., Size or Duration."""

    def __init__(
        self,
        title: str,
        name: str,
        items: Sequence[str | ByteUnit | TimeUnit],
        mapping: dict[str | ByteUnit | TimeUnit, int],
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, name, parent=parent, checkable=True)

        self.mapping = mapping

        self.min_spin = QDoubleSpinBox(minimum=0, maximum=1_000_000)
        init_widget(self.min_spin, f"{name}_minimum")
        set_widget_tips(self.min_spin, f"Minimum value for the {name} filter.")

        self.max_spin = QDoubleSpinBox(minimum=0, maximum=1_000_000)
        init_widget(self.max_spin, f"{name}_maximum")
        set_widget_tips(self.max_spin, f"Maximum value for the {name} filter.")

        self.min_spin.valueChanged.connect(self.max_spin.setMinimum)
        self.max_spin.valueChanged.connect(self.min_spin.setMaximum)

        self.combo = QComboBox()
        self.combo.addItems(items)
        init_widget(self.combo, f"{name}_unit")
        set_widget_tips(self.combo, f"Unit multiplier for the {name} filter.")

        layout = QFormLayout(self)
        layout.addRow("Min", self.min_spin)
        layout.addRow("Max", self.max_spin)
        layout.addRow(self.combo)

    def get_config(self) -> LimitMinMaxModel:
        """Return clean data for the config."""
        mult = self.mapping.get(self.combo.currentText(), 1)
        minimum, maximum = self.min_spin.value() * mult, self.max_spin.value() * mult
        return LimitMinMaxModel(enabled=self.isChecked(), minimum=minimum, maximum=maximum)


class DiversityFilterWidget(BaseGroupBox):
    """Handles logic for diversity range (root/leaf)."""

    def __init__(self, title: str = "Diversity", name: str = "diversity", parent: QWidget | None = None) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, name, parent=parent)

        self.spin_max_per_folder = QSpinBox(minimum=0, maximum=1_000_000)
        init_widget(self.spin_max_per_folder, f"{name}_max_per_folder")
        set_widget_tips(self.spin_max_per_folder, "Maximum number of files allowed per input folder. 0 for unlimited.")

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
        init_widget(self.progbar_total, "progress_total")
        set_widget_tips(self.progbar_total, "Total progress bar, max is set at number of output folders.")

        self.progbar_folder = QProgressBar(value=0, textVisible=True)
        init_widget(self.progbar_folder, "progress_folder")
        set_widget_tips(self.progbar_folder, "Current folder progress bar, max is set at number of files to copy.")

        layout = QFormLayout(self)
        layout.addRow("Total:", self.progbar_total)
        layout.addRow("Folder:", self.progbar_folder)

    @Slot()
    def update_total_prog(self) -> None:
        """Update the total progress bar."""
        self.progbar_total.setValue(self.progbar_total.value() + 1)

    def reset(self) -> None:
        """Reset progress bars."""
        self.progbar_total.setValue(0)
        self.progbar_folder.setValue(0)


class LoggingWidget(QWidget):
    """Logging widget."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the logging widget."""
        super().__init__(parent=parent)
        name = "logging"
        init_widget(self, name)

        self.textbrowser_log = QTextBrowser()
        self.textbrowser_log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        init_widget(self.textbrowser_log, f"{name}_log")
        set_widget_tips(self.textbrowser_log, "Log for output messages.")

        layout = QHBoxLayout(self)
        layout.addWidget(self.textbrowser_log)


class WalkerWidget(BaseGroupBox):
    """Handles logic for filesystem walker settings."""

    def __init__(self, title: str = "Filesystem Walker", name: str = "walker", parent: QWidget | None = None) -> None:
        """Initialize the filesystem walker settings widget."""
        super().__init__(title, name, parent=parent)

        self.chk_follow_symlinks = QCheckBox("Follow Symlinks")
        init_widget(self.chk_follow_symlinks, f"{name}_follow_symlinks")
        set_widget_tips(self.chk_follow_symlinks, "If checked, symbolic links will be followed during file traversal.")

        layout = QFormLayout(self)
        layout.addRow(self.chk_follow_symlinks)

    def get_config(self) -> WalkerModel:
        """Return clean data for the config."""
        return WalkerModel(follow_symlinks=self.chk_follow_symlinks.isChecked())
