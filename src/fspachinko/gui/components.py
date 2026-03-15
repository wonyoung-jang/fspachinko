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

from ..adapters.filesystemport import get_available_transfer_modes, get_icon_path
from ..constants import FilenameTemplate, IconFilename
from .qthelpers import set_qt_tips

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PySide6.QtGui import QDragEnterEvent, QDropEvent


logger = logging.getLogger(__name__)


class BaseGroupBox(QGroupBox):
    """Base class for group boxes with common functionality."""

    def __init__(self, title: str, name: str, *, checkable: bool = False) -> None:
        """Initialize the base group box."""
        super().__init__(title=title)
        self.name = name
        self.setCheckable(checkable)
        self.setFlat(True)

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        return {}

    def restore(self, config: dict) -> None:
        """Restore the widget from config data."""
        msg = f"{self.__class__.__name__} does not implement restore method."
        raise NotImplementedError(msg)


class PathSelectorWidget(BaseGroupBox):
    """Handles logic for selecting a path."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the path selector widget."""
        super().__init__(title, name)
        self.setAcceptDrops(True)
        titlenorm = self.title().casefold()
        self.lbl_selected = QLabel()
        set_qt_tips(self.lbl_selected, f"Select the {titlenorm} folder.")
        icon_browse = QIcon(get_icon_path(IconFilename.BROWSE))
        icon_open = QIcon(get_icon_path(IconFilename.OPEN_DIR))
        self.btn_browse = QPushButton()
        self.btn_browse.setIcon(icon_browse)
        self.btn_browse.clicked.connect(self.browse)
        set_qt_tips(self.btn_browse, f"Browse for {titlenorm} folder.")
        self.btn_open = QPushButton()
        self.btn_open.setIcon(icon_open)
        self.btn_open.clicked.connect(self.open)
        set_qt_tips(self.btn_open, f"Open current {titlenorm} folder in file explorer.")
        layout = QHBoxLayout(self)
        layout.addWidget(self.lbl_selected, stretch=1)
        layout.addWidget(self.btn_browse)
        layout.addWidget(self.btn_open)

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        return {self.name: self.lbl_selected.text()}

    def restore(self, config: dict) -> None:
        """Restore the path selector widget from config data."""
        self.lbl_selected.setText(config.get(self.name, ""))

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


class FileCountWidget(BaseGroupBox):
    """Handles logic for file count settings."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the file count widget."""
        super().__init__(title, name)
        self.radio_fixed = QRadioButton("Fixed")
        self.radio_fixed.setChecked(True)
        set_qt_tips(self.radio_fixed, "Select fixed file count.")
        self.spin_fixed = QSpinBox(suffix=" files", minimum=1)
        set_qt_tips(self.spin_fixed, "Number of files to copy.")
        self.radio_rand = QRadioButton("Random")
        set_qt_tips(self.radio_rand, "Select random file count.")
        self.spin_min_rand = QSpinBox(prefix="Min: ", minimum=1)
        set_qt_tips(self.spin_min_rand, "Minimum random file count.")
        self.spin_max_rand = QSpinBox(prefix="Max: ", minimum=1)
        set_qt_tips(self.spin_max_rand, "Maximum random file count.")
        self.spin_min_rand.valueChanged.connect(self.spin_max_rand.setMinimum)
        self.spin_max_rand.valueChanged.connect(self.spin_min_rand.setMaximum)
        self.radio_fixed.toggled.connect(self.spin_fixed.setEnabled)
        self.radio_fixed.toggled.connect(self.spin_min_rand.setDisabled)
        self.radio_fixed.toggled.connect(self.spin_max_rand.setDisabled)
        self.spin_min_rand.setDisabled(True)
        self.spin_max_rand.setDisabled(True)
        layout = QGridLayout(self)
        layout.addWidget(self.radio_fixed, 0, 0)
        layout.addWidget(self.spin_fixed, 0, 1)
        layout.addWidget(self.radio_rand, 1, 0)
        layout.addWidget(self.spin_min_rand, 1, 1)
        layout.addWidget(self.spin_max_rand, 2, 1)

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        return {
            self.name: {
                "count": self.spin_fixed.value(),
                "is_rand_enabled": self.radio_rand.isChecked(),
                "rand_min": self.spin_min_rand.value(),
                "rand_max": self.spin_max_rand.value(),
            }
        }

    def restore(self, config: dict) -> None:
        """Restore the file count widget from config data."""
        c = config.get(self.name, {})
        self.spin_fixed.setValue(c.get("count", 1))
        self.radio_fixed.setChecked(not c.get("is_rand_enabled", True))
        self.radio_rand.setChecked(c.get("is_rand_enabled", True))
        self.spin_min_rand.setValue(c.get("rand_min", 1))
        self.spin_max_rand.setValue(c.get("rand_max", 1))


class DirectoryCreateWidget(BaseGroupBox):
    """Handles logic for creating folders."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the create folders widget."""
        super().__init__(title, name, checkable=True)
        self.spinbox_folder_count = QSpinBox(suffix=" directories", minimum=1)
        set_qt_tips(self.spinbox_folder_count, "Number of folders to create.")
        self.lineedit_folder_name = QLineEdit(placeholderText="Ex: Random_Files", clearButtonEnabled=True)
        set_qt_tips(self.lineedit_folder_name, "Template for naming created folders.")
        layout = QVBoxLayout(self)
        layout.addWidget(self.spinbox_folder_count)
        layout.addWidget(self.lineedit_folder_name)

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        return {
            self.name: {
                "is_enabled": self.isChecked(),
                "name": self.lineedit_folder_name.text(),
                "count": self.spinbox_folder_count.value(),
            }
        }

    def restore(self, config: dict) -> None:
        """Restore the create folders widget from config data."""
        c = config.get(self.name, {})
        self.setChecked(c.get("is_enabled", False))
        self.spinbox_folder_count.setValue(c.get("count", 1))
        self.lineedit_folder_name.setText(c.get("name", ""))


class FilenamerWidget(BaseGroupBox):
    """Handles logic for filename template settings."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the filename template settings widget."""
        super().__init__(title, name, checkable=True)
        self.edit_template = QLineEdit("{original}", placeholderText="Ex: {original}_{index}", clearButtonEnabled=True)
        set_qt_tips(self.edit_template, "Template for renaming files. Use the 'Insert Tag' button to add tags.")
        self.menu_template = QMenu(title="Tags")
        set_qt_tips(self.menu_template, "Select a tag to insert into the filename template.")
        self.btn_template = QPushButton("Insert tag")
        self.btn_template.setMenu(self.menu_template)
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

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        return {
            self.name: {
                "is_enabled": self.isChecked(),
                "template": self.edit_template.text(),
            }
        }

    def restore(self, config: dict) -> None:
        """Restore the filename template widget from config data."""
        c = config.get(self.name, {})
        self.setChecked(c.get("is_enabled", False))
        self.edit_template.setText(c.get("template", ""))


class TextFilterWidget(BaseGroupBox):
    """Handles the Include/Exclude text pattern."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the dual list widget."""
        super().__init__(title, name, checkable=True)
        title_lower = self.title().casefold()
        self.filter_edit = QLineEdit(placeholderText="comma,separated,items", clearButtonEnabled=True)
        set_qt_tips(self.filter_edit, f"Enter {title_lower} separated by commas.")
        self.filter_include_radio = QRadioButton("Include")
        self.filter_include_radio.setChecked(True)
        set_qt_tips(self.filter_include_radio, f"Include only items matching the {title_lower} filter.")
        self.filter_exclude_radio = QRadioButton("Exclude")
        set_qt_tips(self.filter_exclude_radio, f"Exclude items matching the {title_lower} filter.")
        layout = QHBoxLayout(self)
        layout.addWidget(self.filter_edit)
        layout.addWidget(self.filter_include_radio)
        layout.addWidget(self.filter_exclude_radio)

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        return {
            self.name: {
                "is_enabled": self.isChecked(),
                "should_include": self.filter_include_radio.isChecked(),
                "text": self.filter_edit.text(),
            }
        }

    def restore(self, config: dict) -> None:
        """Restore the text filter widget from config data."""
        c = config.get(self.name, {})
        self.setChecked(c.get("is_enabled", False))
        self.filter_include_radio.setChecked(c.get("should_include", True))
        self.filter_exclude_radio.setChecked(not c.get("should_include", True))
        self.filter_edit.setText(c.get("text", ""))


class RangeFilterWidget(BaseGroupBox):
    """Handles logic for ranges (min/max), e.g., Size or Duration."""

    def __init__(self, title: str, name: str, items: Sequence[str]) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, name, checkable=True)
        self.spin_min = QDoubleSpinBox(prefix="Min ")
        set_qt_tips(self.spin_min, f"Minimum value for the {name} filter.")
        self.spin_max = QDoubleSpinBox(prefix="Max ")
        set_qt_tips(self.spin_max, f"Maximum value for the {name} filter.")
        self.spin_min.valueChanged.connect(self.spin_max.setMinimum)
        self.spin_max.valueChanged.connect(self.spin_min.setMaximum)
        self.combo_unit = QComboBox()
        self.combo_unit.addItems(items)
        set_qt_tips(self.combo_unit, f"Unit multiplier for the {name} filter.")
        layout = QHBoxLayout(self)
        layout.addWidget(self.spin_min)
        layout.addWidget(self.spin_max)
        layout.addWidget(self.combo_unit)

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        return {
            self.name: {
                "is_enabled": self.isChecked(),
                "minimum": self.spin_min.value(),
                "maximum": self.spin_max.value(),
                "unit": self.combo_unit.currentText(),
            }
        }

    def restore(self, config: dict) -> None:
        """Restore the range filter widget from config data."""
        c = config.get(self.name, {})
        self.setChecked(c.get("is_enabled", False))
        self.spin_min.setValue(c.get("minimum", 0.0))
        self.spin_max.setValue(c.get("maximum", 10.0))
        unit = c.get("unit", "")
        index = self.combo_unit.findText(unit)
        if index != -1:
            self.combo_unit.setCurrentIndex(index)


class OptionsWidget(BaseGroupBox):
    """Handles logic for miscellaneous options."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the options widget."""
        super().__init__(title, name)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(list(get_available_transfer_modes().keys()))
        set_qt_tips(self.combo_mode, "Select the transfer mode to use.")
        self.spin_max_per_folder = QSpinBox()
        self.spin_max_per_folder.setSpecialValueText("Unlimited")
        set_qt_tips(self.spin_max_per_folder, "Maximum number of files allowed per input folder. 0 for unlimited.")
        self.chk_follow_symlink = QCheckBox()
        set_qt_tips(self.chk_follow_symlink, "If checked, symbolic links will be followed during file traversal.")
        self.rng_seed = QLineEdit(placeholderText="RNG Seed (optional)", clearButtonEnabled=True)
        set_qt_tips(self.rng_seed, "Seed for random number generator. Integer or string. If empty, system clock used.")
        self.chk_unique_folders = QCheckBox()
        set_qt_tips(self.chk_unique_folders, "If checked, created folder names will have unique files.")
        layout = QFormLayout(self)
        layout.addRow("Transfer mode", self.combo_mode)
        layout.addRow("Max from one directory", self.spin_max_per_folder)
        layout.addRow("Ensure unique directories", self.chk_unique_folders)
        layout.addRow("Follow symbolic links", self.chk_follow_symlink)
        layout.addRow("Random seed", self.rng_seed)

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        return {
            self.name: {
                "transfer_mode": self.combo_mode.currentText(),
                "max_per_dir": self.spin_max_per_folder.value(),
                "is_create_unique_dirs": self.chk_unique_folders.isChecked(),
                "should_follow_symlink": self.chk_follow_symlink.isChecked(),
                "rng_seed": self.rng_seed.text(),
            }
        }

    def restore(self, config: dict) -> None:
        """Restore the options widget from config data."""
        c = config.get(self.name, {})
        self.combo_mode.setCurrentText(c.get("transfer_mode", ""))
        self.spin_max_per_folder.setValue(c.get("max_per_dir", 0))
        self.chk_unique_folders.setChecked(c.get("is_create_unique_dirs", False))
        self.chk_follow_symlink.setChecked(c.get("should_follow_symlink", False))
        self.rng_seed.setText(c.get("rng_seed", ""))


class LogWidget(QWidget):
    """Logging text box."""

    def __init__(self) -> None:
        """Initialize the log widget."""
        super().__init__()
        self.textbrowser_log = QTextBrowser()
        self.textbrowser_log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        set_qt_tips(self.textbrowser_log, "Log for output messages.")
        layout = QHBoxLayout(self)
        layout.addWidget(self.textbrowser_log)

    def append(self, text: str) -> None:
        """Append text to the log."""
        self.textbrowser_log.append(text)


class ProgressWidget(QWidget):
    """Progress bars."""

    def __init__(self) -> None:
        """Initialize the progress widget."""
        super().__init__()
        self.progbar_dirs = QProgressBar(textVisible=True)
        set_qt_tips(self.progbar_dirs, "Total progress bar, max is set at number of output folders.")
        self.progbar_files = QProgressBar(textVisible=True)
        set_qt_tips(self.progbar_files, "Current folder progress bar, max is set at number of files to copy.")
        layout = QFormLayout(self)
        layout.addRow("Directories", self.progbar_dirs)
        layout.addRow("Files", self.progbar_files)

    def handle_start_process(self, dir_count: int) -> None:
        """Set up the progress bars at the start of the process."""
        self.progbar_dirs.setMaximum(dir_count)
        self.progbar_dirs.setValue(0)
        self.progbar_files.setValue(0)

    def handle_directory_start(self, target: int) -> None:
        """Update the directory progress bar."""
        curr = self.progbar_dirs.value()
        self.progbar_dirs.setValue(curr + 1)
        self.progbar_files.setMaximum(target)
        self.progbar_files.setValue(0)

    def handle_file_transfer(self) -> int:
        """Update the file progress bar."""
        curr = self.progbar_files.value()
        self.progbar_files.setValue(curr + 1)
        maximum = self.progbar_files.maximum()
        return int((curr + 1) * 100 / maximum) if maximum > 0 else 0
