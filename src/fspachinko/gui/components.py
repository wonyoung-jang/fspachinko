"""GUI components in PySide6."""

import logging
import os
from typing import TYPE_CHECKING

from PySide6.QtCore import QUrl, Slot
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
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

from ..adapters import get_available_transfer_modes
from ..core import (
    ByteUnit,
    DirectoryModel,
    FilecountModel,
    FilenameModel,
    FilenameTemplate,
    IconFilename,
    OptionsModel,
    RangeFilterModel,
    TextFilterModel,
    TimeUnit,
    get_icon_path,
)
from .qthelpers import set_qt_name, set_qt_tips

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PySide6.QtGui import QDragEnterEvent, QDropEvent


logger = logging.getLogger(__name__)


class BaseGroupBox(QGroupBox):
    """Base class for group boxes with common functionality."""

    def __init__(self, title: str, name: str, *, checkable: bool = False) -> None:
        """Initialize the base group box."""
        super().__init__(title=title)
        set_qt_name(self, name)
        self.setCheckable(checkable)
        self.setFlat(True)


class PathSelectorWidget(BaseGroupBox):
    """Handles logic for selecting a path."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the path selector widget."""
        super().__init__(title=title, name=name)
        self.setAcceptDrops(True)

        titlenorm = self.title().casefold()

        self.lbl_selected = QLabel()
        set_qt_name(self.lbl_selected, f"{name}_label")
        set_qt_tips(self.lbl_selected, f"Select the {titlenorm} folder.")

        icon_browse = QIcon(get_icon_path(IconFilename.BROWSE))
        icon_open = QIcon(get_icon_path(IconFilename.OPEN_DIR))

        self.btn_browse = QPushButton()
        self.btn_browse.setIcon(icon_browse)
        self.btn_browse.clicked.connect(self.browse)
        set_qt_name(self.btn_browse, f"{name}_browse_btn")
        set_qt_tips(self.btn_browse, f"Browse for {titlenorm} folder.")

        self.btn_open = QPushButton()
        self.btn_open.setIcon(icon_open)
        self.btn_open.clicked.connect(self.open)
        set_qt_name(self.btn_open, f"{name}_open_btn")
        set_qt_tips(self.btn_open, f"Open current {titlenorm} folder in file explorer.")

        layout = QHBoxLayout(self)
        layout.addWidget(self.lbl_selected, stretch=1)
        layout.addWidget(self.btn_browse)
        layout.addWidget(self.btn_open)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        """Handle drag enter event for folder paths."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """Handle drop event for folder paths."""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self.lbl_selected.setText(path)

    @Slot()
    def browse(self) -> None:
        """Return the browse button."""
        d = QFileDialog.getExistingDirectory(
            parent=self,
            caption=f"Select {self.title()}",
            dir=self.lbl_selected.text(),
        )
        if d:
            self.lbl_selected.setText(d)

    @Slot()
    def open(self) -> None:
        """Open the currently selected path in file explorer."""
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.lbl_selected.text()))
        except Exception:
            logger.exception("Failed to open path %s", self.lbl_selected.text())

    def get_config(self) -> str:
        """Return clean data for the config."""
        return self.lbl_selected.text()


class RootPathSelectorWidget(PathSelectorWidget):
    """Handles logic for selecting a root path."""

    def __init__(self) -> None:
        """Initialize the root path selector widget."""
        super().__init__(title="Root", name="root")


class DestPathSelectorWidget(PathSelectorWidget):
    """Handles logic for selecting a destination path."""

    def __init__(self) -> None:
        """Initialize the destination path selector widget."""
        super().__init__(title="Destination", name="dest")


class FileCountWidget(BaseGroupBox):
    """Handles logic for file count settings."""

    def __init__(self, title: str = "File count", name: str = "filecount") -> None:
        """Initialize the file count widget."""
        super().__init__(title=title, name=name)

        self.radio_fixed = QRadioButton("Fixed")
        self.radio_fixed.setChecked(True)
        set_qt_name(self.radio_fixed, f"{name}_fixed_chk")
        set_qt_tips(self.radio_fixed, "Select fixed file count.")

        self.spin_fixed = QSpinBox(suffix=" files", minimum=1)
        set_qt_name(self.spin_fixed, f"{name}_fixed_val")
        set_qt_tips(self.spin_fixed, "Number of files to copy.")

        self.radio_rand = QRadioButton("Random")
        set_qt_name(self.radio_rand, f"{name}_rand_chk")
        set_qt_tips(self.radio_rand, "Select random file count.")

        self.spin_min_rand = QSpinBox(prefix="Min: ", minimum=1)
        set_qt_name(self.spin_min_rand, f"{name}_rand_min")
        set_qt_tips(self.spin_min_rand, "Minimum random file count.")

        self.spin_max_rand = QSpinBox(prefix="Max: ", minimum=1)
        set_qt_name(self.spin_max_rand, f"{name}_rand_max")
        set_qt_tips(self.spin_max_rand, "Maximum random file count.")

        self.spin_min_rand.valueChanged.connect(self.spin_max_rand.setMinimum)
        self.spin_max_rand.valueChanged.connect(self.spin_min_rand.setMaximum)

        self.radio_fixed.toggled.connect(self.spin_fixed.setEnabled)
        self.radio_fixed.toggled.connect(self.spin_min_rand.setDisabled)
        self.radio_fixed.toggled.connect(self.spin_max_rand.setDisabled)

        # Initial state
        self.spin_min_rand.setDisabled(True)
        self.spin_max_rand.setDisabled(True)

        layout = QGridLayout(self)
        layout.addWidget(self.radio_fixed, 0, 0)
        layout.addWidget(self.spin_fixed, 0, 1)
        layout.addWidget(self.radio_rand, 1, 0)
        layout.addWidget(self.spin_min_rand, 1, 1)
        layout.addWidget(self.spin_max_rand, 2, 1)

    def get_config(self) -> FilecountModel:
        """Return clean data for the config."""
        return FilecountModel(
            count=self.spin_fixed.value(),
            is_rand_enabled=self.radio_rand.isChecked(),
            rand_min=self.spin_min_rand.value(),
            rand_max=self.spin_max_rand.value(),
        )


class DirectoryCreateWidget(BaseGroupBox):
    """Handles logic for creating folders."""

    def __init__(self, title: str = "Create directories", name: str = "directory") -> None:
        """Initialize the create folders widget."""
        super().__init__(title=title, name=name, checkable=True)

        self.spinbox_folder_count = QSpinBox(suffix=" directories", minimum=1)
        set_qt_name(self.spinbox_folder_count, f"{name}_count")
        set_qt_tips(self.spinbox_folder_count, "Number of folders to create.")

        self.lineedit_folder_name = QLineEdit(placeholderText="Ex: Random_Files", clearButtonEnabled=True)
        set_qt_name(self.lineedit_folder_name, f"{name}_name")
        set_qt_tips(self.lineedit_folder_name, "Template for naming created folders.")

        layout = QVBoxLayout(self)
        layout.addWidget(self.spinbox_folder_count)
        layout.addWidget(self.lineedit_folder_name)

    def get_config(self) -> DirectoryModel:
        """Return clean data for the config."""
        return DirectoryModel(
            is_enabled=self.isChecked(),
            name=self.lineedit_folder_name.text(),
            count=self.spinbox_folder_count.value() if self.isChecked() else 1,
        )


class FilenamerWidget(BaseGroupBox):
    """Handles logic for filename template settings."""

    def __init__(self, title: str = "Filenamer", name: str = "filenamer") -> None:
        """Initialize the filename template settings widget."""
        super().__init__(title=title, name=name, checkable=True)

        self.edit_template = QLineEdit("{original}", placeholderText="Ex: {original}_{index}", clearButtonEnabled=True)
        set_qt_name(self.edit_template, f"{name}_template")
        set_qt_tips(self.edit_template, "Template for renaming files. Use the 'Insert Tag' button to add tags.")

        self.menu_template = QMenu(title="Tags")
        set_qt_name(self.menu_template, f"{name}_template_menu")
        set_qt_tips(self.menu_template, "Select a tag to insert into the filename template.")

        self.btn_template = QPushButton("Insert tag")
        self.btn_template.setMenu(self.menu_template)
        set_qt_name(self.btn_template, f"{name}_template_button")
        set_qt_tips(self.btn_template, "Insert a tag into the template at the cursor position.")

        for lbl in FilenameTemplate:
            action = self.menu_template.addAction(lbl)
            action.triggered.connect(lambda _, tag=lbl: self.insert_tag(tag))

        layout = QHBoxLayout(self)
        layout.addWidget(self.edit_template)
        layout.addWidget(self.btn_template)

    @Slot(str)
    def insert_tag(self, tag: str) -> None:
        """Insert a tag into the template at the cursor position."""
        self.edit_template.insert(tag)
        self.edit_template.setFocus()

    def get_config(self) -> FilenameModel:
        """Return clean data for the config."""
        return FilenameModel(
            is_enabled=self.isChecked(),
            template=self.edit_template.text().strip() or "{original}",
        )


class TextFilterWidget(BaseGroupBox):
    """Handles the Include/Exclude text pattern."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the dual list widget."""
        super().__init__(title, name, checkable=True)

        title_lower = self.title().casefold()

        self.filter_edit = QLineEdit(placeholderText="comma,separated,items", clearButtonEnabled=True)
        set_qt_name(self.filter_edit, f"{name}_text")
        set_qt_tips(self.filter_edit, f"Enter {title_lower} separated by commas.")

        self.filter_include_radio = QRadioButton("Include")
        self.filter_include_radio.setChecked(True)
        set_qt_name(self.filter_include_radio, f"{name}_include")
        set_qt_tips(self.filter_include_radio, f"Include only items matching the {title_lower} filter.")

        self.filter_exclude_radio = QRadioButton("Exclude")
        set_qt_name(self.filter_exclude_radio, f"{name}_exclude")
        set_qt_tips(self.filter_exclude_radio, f"Exclude items matching the {title_lower} filter.")

        layout = QHBoxLayout(self)
        layout.addWidget(self.filter_edit)
        layout.addWidget(self.filter_include_radio)
        layout.addWidget(self.filter_exclude_radio)

    def get_config(self) -> TextFilterModel:
        """Return clean data for the config."""
        return TextFilterModel(
            is_enabled=self.isChecked(),
            should_include=self.filter_include_radio.isChecked(),
            text=self.filter_edit.text(),
        )


class DirnameFilterWidget(TextFilterWidget):
    """Handles the Include/Exclude pattern for directory names."""

    def __init__(self) -> None:
        """Initialize the directory filter widget."""
        super().__init__(title="Directory name", name="directory_name_filter")


class ExtensionFilterWidget(TextFilterWidget):
    """Handles the Include/Exclude pattern for file extensions."""

    def __init__(self) -> None:
        """Initialize the extensions filter widget."""
        super().__init__(title="Extensions", name="extension")


class KeywordFilterWidget(TextFilterWidget):
    """Handles the Include/Exclude pattern for keywords."""

    def __init__(self) -> None:
        """Initialize the keywords filter widget."""
        super().__init__(title="Keywords", name="keyword")


class RangeFilterWidget(BaseGroupBox):
    """Handles logic for ranges (min/max), e.g., Size or Duration."""

    def __init__(self, title: str, name: str, items: Sequence[str | ByteUnit | TimeUnit]) -> None:
        """Initialize the range filter widget."""
        super().__init__(title=title, name=name, checkable=True)

        self.spin_min = QDoubleSpinBox(prefix="Min ")
        set_qt_name(self.spin_min, f"{name}_minimum")
        set_qt_tips(self.spin_min, f"Minimum value for the {name} filter.")

        self.spin_max = QDoubleSpinBox(prefix="Max ")
        set_qt_name(self.spin_max, f"{name}_maximum")
        set_qt_tips(self.spin_max, f"Maximum value for the {name} filter.")

        self.spin_min.valueChanged.connect(self.spin_max.setMinimum)
        self.spin_max.valueChanged.connect(self.spin_min.setMaximum)

        self.combo_unit = QComboBox()
        self.combo_unit.addItems(items)
        set_qt_name(self.combo_unit, f"{name}_unit")
        set_qt_tips(self.combo_unit, f"Unit multiplier for the {name} filter.")

        layout = QHBoxLayout(self)
        layout.addWidget(self.spin_min)
        layout.addWidget(self.spin_max)
        layout.addWidget(self.combo_unit)

    def get_config(self) -> RangeFilterModel:
        """Return clean data for the config."""
        return RangeFilterModel(
            is_enabled=self.isChecked(),
            minimum=self.spin_min.value(),
            maximum=self.spin_max.value(),
            unit=self.combo_unit.currentText(),
        )


class SizeFilterWidget(RangeFilterWidget):
    """Handles logic for size range filter."""

    def __init__(self) -> None:
        """Initialize the size filter widget."""
        super().__init__(title="File Size", name="filesize", items=tuple(ByteUnit))


class DurationFilterWidget(RangeFilterWidget):
    """Handles logic for duration range filter."""

    def __init__(self) -> None:
        """Initialize the duration filter widget."""
        super().__init__(title="Duration", name="duration", items=tuple(TimeUnit))


class OptionsWidget(BaseGroupBox):
    """Handles logic for miscellaneous options."""

    def __init__(self, title: str = "Options", name: str = "options") -> None:
        """Initialize the options widget."""
        super().__init__(title=title, name=name)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(list(get_available_transfer_modes().keys()))
        set_qt_name(self.combo_mode, f"{name}_transfer_mode")
        set_qt_tips(self.combo_mode, "Select the transfer mode to use.")

        self.spin_max_per_folder = QSpinBox()
        self.spin_max_per_folder.setSpecialValueText("Unlimited")
        set_qt_name(self.spin_max_per_folder, f"{name}_max_per_folder")
        set_qt_tips(self.spin_max_per_folder, "Maximum number of files allowed per input folder. 0 for unlimited.")

        self.chk_follow_symlink = QCheckBox()
        set_qt_name(self.chk_follow_symlink, f"{name}_should_follow_symlink")
        set_qt_tips(self.chk_follow_symlink, "If checked, symbolic links will be followed during file traversal.")

        self.rng_seed = QLineEdit(placeholderText="RNG Seed (optional)", clearButtonEnabled=True)
        set_qt_name(self.rng_seed, f"{name}_rng_seed")
        set_qt_tips(
            self.rng_seed,
            "Optional seed for random number generator. Can be an integer or string. "
            "If empty, a random seed will be used.",
        )

        self.chk_unique_folders = QCheckBox()
        set_qt_name(self.chk_unique_folders, f"{name}_unique")
        set_qt_tips(self.chk_unique_folders, "If checked, created folder names will have unique files.")

        layout = QFormLayout(self)
        layout.addRow("Transfer mode", self.combo_mode)
        layout.addRow("Max from one directory", self.spin_max_per_folder)
        layout.addRow("Ensure unique directories", self.chk_unique_folders)
        layout.addRow("Follow symbolic links", self.chk_follow_symlink)
        layout.addRow("Random seed", self.rng_seed)

    def get_config(self) -> OptionsModel:
        """Return clean data for the config."""
        return OptionsModel(
            transfer_mode=self.combo_mode.currentText(),
            max_per_dir=self.spin_max_per_folder.value(),
            is_create_unique_dirs=self.chk_unique_folders.isChecked(),
            should_follow_symlink=self.chk_follow_symlink.isChecked(),
            rng_seed=self.rng_seed.text() or None,
        )


class ProgressWidget(QWidget):
    """Progress bars and execution controls."""

    def __init__(self, name: str = "progress") -> None:
        """Post-initialize the progress widget."""
        super().__init__()
        set_qt_name(self, name)

        self.progbar_dirs = QProgressBar(textVisible=True)
        set_qt_name(self.progbar_dirs, f"{name}_directories")
        set_qt_tips(self.progbar_dirs, "Total progress bar, max is set at number of output folders.")

        self.progbar_files = QProgressBar(textVisible=True)
        set_qt_name(self.progbar_files, f"{name}_files")
        set_qt_tips(self.progbar_files, "Current folder progress bar, max is set at number of files to copy.")

        layout = QFormLayout(self)
        layout.addRow("Directories", self.progbar_dirs)
        layout.addRow("Files", self.progbar_files)

    def reset(self) -> None:
        """Reset progress bars."""
        self.progbar_dirs.setValue(0)
        self.progbar_files.setValue(0)

    @Slot(int, int)
    def start_directory(self, idx: int, nfiles: int) -> None:
        """Start processing a directory."""
        self.progbar_dirs.setValue(idx)
        self.progbar_files.setMaximum(nfiles)


class LogWidget(QWidget):
    """Log widget."""

    def __init__(self, name: str = "logging") -> None:
        """Initiralize the log widget."""
        super().__init__()
        set_qt_name(self, name)

        self.textbrowser_log = QTextBrowser()
        self.textbrowser_log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        set_qt_name(self.textbrowser_log, f"{name}_log")
        set_qt_tips(self.textbrowser_log, "Log for output messages.")

        layout = QHBoxLayout(self)
        layout.addWidget(self.textbrowser_log)
