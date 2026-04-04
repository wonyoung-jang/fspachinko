"""GUI components in PySide6."""

from dataclasses import dataclass
from functools import cache
from os.path import exists, isdir
from typing import TYPE_CHECKING, ClassVar

from PySide6.QtCore import QUrl, Slot
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
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

from fspachinko.adapters.transfer import available_transfer_fns
from fspachinko.constants import SIZE_MAP, TIME_MAP, FilenameTemplate, TransferMode
from fspachinko.entrypoints.gui.helpers import get_icon, get_shortcut, set_qt_tips

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PySide6.QtGui import QDragEnterEvent, QDropEvent


@dataclass(slots=True)
class Actions:
    """Main file menu actions."""

    save: QAction
    save_as: QAction
    load: QAction
    exit: QAction
    start: QAction
    stop: QAction
    _CONFIG: ClassVar[dict[str, tuple[str, str]]] = {
        "save": ("&Save Configuration", "Save current configuration (Ctrl+S)"),
        "save_as": ("Save Configuration &As", "Save current configuration as ... (Ctrl+Shift+S)"),
        "load": ("&Load Configuration", "Load configuration (Ctrl+O)"),
        "exit": ("&Exit", "Exit application (Ctrl+W)"),
        "start": ("&Start", "Start (Ctrl+R)"),
        "stop": ("S&top", "Stop (ESC)"),
    }

    @classmethod
    def build(cls) -> Actions:
        """Get file menu actions."""
        actions = {}
        for name, (text, tip) in cls._CONFIG.items():
            action = QAction(get_icon(name), text, shortcut=get_shortcut(name))
            set_qt_tips(action, tip)
            actions[name] = action
        return cls(**actions)


class BaseDockWidget(QDockWidget):
    """Base class for dock widgets with common functionality."""

    def __init__(self, w: QWidget, name: str) -> None:
        """Initialize the base dock widget."""
        super().__init__()
        self.setWidget(w)
        self.setObjectName(name)


class BaseGroupBox(QGroupBox):
    """Base class for group boxes with common functionality."""

    def __init__(self, title: str, name: str, *, checkable: bool = False) -> None:
        """Initialize the base group box."""
        super().__init__(title=title, checkable=checkable, flat=True)
        self.name = name

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        raise NotImplementedError

    def restore(self, config: dict) -> None:
        """Restore the widget from config data."""
        raise NotImplementedError

    def _section(self, config: dict) -> dict:
        """Get the relevant section of the config."""
        return config.get(self.name, {})


class PathSelectorWidget(BaseGroupBox):
    """Handles logic for selecting a path."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the path selector widget."""
        super().__init__(title, name)
        self.lbl_selected = QLabel()
        self.btn_browse = QPushButton(get_icon("browse"), "Browse")
        self.btn_open = QPushButton(get_icon("open_dir"), "Open")
        self.setAcceptDrops(True)
        self.btn_browse.clicked.connect(self.browse)
        self.btn_open.clicked.connect(self.open)
        titlenorm = self.title().casefold()
        set_qt_tips(self.lbl_selected, f"Select the {titlenorm} folder.")
        set_qt_tips(self.btn_browse, f"Browse for {titlenorm} folder.")
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
            caption=f"Select {self.title()}",
            dir=self.lbl_selected.text(),
        )
        if d:
            self.lbl_selected.setText(d)

    @Slot()
    def open(self) -> None:
        """Open the currently selected path in file explorer."""
        path = self.lbl_selected.text()
        if not path or not exists(path):
            msg = f"Cannot open {self.title().casefold()} folder. No valid path selected."
            raise FileNotFoundError(msg)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        """Handle drag enter event for folder paths."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """Handle drop event for folder paths."""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if isdir(path):
                self.lbl_selected.setText(path)


class FileCountWidget(BaseGroupBox):
    """Handles logic for file count settings."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the file count widget."""
        super().__init__(title, name)
        self.radio_fixed = QRadioButton("Fixed")
        self.spin_fixed = QSpinBox(suffix=" files", minimum=1)
        self.radio_rand = QRadioButton("Random")
        self.spin_min_rand = QSpinBox(prefix="Min: ", minimum=1)
        self.spin_max_rand = QSpinBox(prefix="Max: ", minimum=2)
        self.spin_min_rand.valueChanged.connect(self.spin_max_rand.setMinimum)
        self.spin_max_rand.valueChanged.connect(self.spin_min_rand.setMaximum)
        self.radio_fixed.toggled.connect(self.spin_fixed.setEnabled)
        self.radio_fixed.toggled.connect(self.spin_min_rand.setDisabled)
        self.radio_fixed.toggled.connect(self.spin_max_rand.setDisabled)
        set_qt_tips(self.radio_fixed, "Select fixed file count.")
        set_qt_tips(self.spin_fixed, "Number of files to copy.")
        set_qt_tips(self.radio_rand, "Select random file count.")
        set_qt_tips(self.spin_min_rand, "Minimum random file count.")
        set_qt_tips(self.spin_max_rand, "Maximum random file count.")
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
            },
        }

    def restore(self, config: dict) -> None:
        """Restore the file count widget from config data."""
        c = self._section(config)
        is_rand_enabled = c.get("is_rand_enabled", False)
        self.spin_fixed.setValue(c.get("count", 1))
        self.radio_fixed.setChecked(not is_rand_enabled)
        self.radio_rand.setChecked(is_rand_enabled)
        self.spin_min_rand.setValue(c.get("rand_min", 1))
        self.spin_max_rand.setValue(c.get("rand_max", 10))
        self.spin_min_rand.setEnabled(is_rand_enabled)
        self.spin_max_rand.setEnabled(is_rand_enabled)


class DirectoryCreateWidget(BaseGroupBox):
    """Handles logic for creating folders."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the create folders widget."""
        super().__init__(title, name, checkable=True)
        self.spinbox_folder_count = QSpinBox(suffix=" directories", minimum=1)
        self.lineedit_folder_name = QLineEdit(placeholderText="Ex: Random_Files", clearButtonEnabled=True)
        set_qt_tips(self.spinbox_folder_count, "Number of folders to create.")
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
                "count": self.spinbox_folder_count.value(),
                "name": self.lineedit_folder_name.text(),
            },
        }

    def restore(self, config: dict) -> None:
        """Restore the create folders widget from config data."""
        c = self._section(config)
        self.setChecked(c.get("is_enabled", False))
        self.spinbox_folder_count.setValue(c.get("count", 1))
        self.lineedit_folder_name.setText(c.get("name", "fsp_output"))


class FilenamerWidget(BaseGroupBox):
    """Handles logic for filename template settings."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the filename template settings widget."""
        super().__init__(title, name, checkable=True)
        self.lineedit_template = QLineEdit(
            placeholderText=f"Ex: {FilenameTemplate.ORIGINAL}_{FilenameTemplate.INDEX}",
            clearButtonEnabled=True,
        )
        self.btn_insert = QPushButton("Insert tag")
        self.menu = QMenu(title="Tags")
        for lbl in FilenameTemplate:
            action = self.menu.addAction(lbl)
            action.triggered.connect(lambda _, tag=lbl: self.insert_tag(tag))
        self.btn_insert.setMenu(self.menu)
        set_qt_tips(self.lineedit_template, "Template for renaming files. Use the 'Insert Tag' button to add tags.")
        set_qt_tips(self.btn_insert, "Insert a tag into the template at the cursor position.")
        set_qt_tips(self.menu, "Select a tag to insert into the filename template.")
        layout = QHBoxLayout(self)
        layout.addWidget(self.lineedit_template)
        layout.addWidget(self.btn_insert)

    @Slot(str)
    def insert_tag(self, tag: str) -> None:
        """Insert a tag into the template at the cursor position."""
        self.lineedit_template.insert(tag)
        self.lineedit_template.setFocus()

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        return {
            self.name: {
                "is_enabled": self.isChecked(),
                "template": self.lineedit_template.text(),
            },
        }

    def restore(self, config: dict) -> None:
        """Restore the filename template widget from config data."""
        c = self._section(config)
        self.setChecked(c.get("is_enabled", False))
        self.lineedit_template.setText(c.get("template", FilenameTemplate.ORIGINAL))


class TextFilterWidget(BaseGroupBox):
    """Handles the Include/Exclude text pattern."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the dual list widget."""
        super().__init__(title, name, checkable=True)
        self.lineedit_filter = QLineEdit(placeholderText="comma,separated,items", clearButtonEnabled=True)
        self.radio_include = QRadioButton("Include")
        self.radio_exclude = QRadioButton("Exclude")
        set_qt_tips(self.lineedit_filter, f"Enter {name}s separated by commas.")
        set_qt_tips(self.radio_include, f"Include only items matching the {name}s filter.")
        set_qt_tips(self.radio_exclude, f"Exclude items matching the {name}s filter.")
        layout = QHBoxLayout(self)
        layout.addWidget(self.lineedit_filter)
        layout.addWidget(self.radio_include)
        layout.addWidget(self.radio_exclude)

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        return {
            self.name: {
                "is_enabled": self.isChecked(),
                "should_include": self.radio_include.isChecked(),
                "text": self.lineedit_filter.text(),
            },
        }

    def restore(self, config: dict) -> None:
        """Restore the text filter widget from config data."""
        c = self._section(config)
        should_include = c.get("should_include", True)
        self.setChecked(c.get("is_enabled", False))
        self.radio_include.setChecked(should_include)
        self.radio_exclude.setChecked(not should_include)
        self.lineedit_filter.setText(c.get("text", ""))


class RangeFilterWidget(BaseGroupBox):
    """Handles logic for ranges (min/max), e.g., Size or Duration."""

    def __init__(self, title: str, name: str, items: Sequence[str]) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, name, checkable=True)
        self.spin_min = QDoubleSpinBox(prefix="Min: ")
        self.spin_max = QDoubleSpinBox(prefix="Max: ")
        self.combo_unit = QComboBox()
        self.combo_unit.addItems(items)
        set_qt_tips(self.spin_min, f"Minimum value for the {name} filter.")
        set_qt_tips(self.spin_max, f"Maximum value for the {name} filter.")
        set_qt_tips(self.combo_unit, f"Unit multiplier for the {name} filter.")
        self.spin_min.valueChanged.connect(self.spin_max.setMinimum)
        self.spin_max.valueChanged.connect(self.spin_min.setMaximum)
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
            },
        }

    def restore(self, config: dict) -> None:
        """Restore the range filter widget from config data."""
        c = self._section(config)
        self.setChecked(c.get("is_enabled", False))
        self.spin_min.setValue(c.get("minimum", 0.0))
        self.spin_max.setValue(c.get("maximum", 10.0))
        unit = c.get("unit", "")
        index = self.combo_unit.findText(unit)
        if index != -1:
            self.combo_unit.setCurrentIndex(index)


class OptionsWidget(BaseGroupBox):
    """Handles logic for miscellaneous options."""

    def __init__(self, title: str, name: str, transfermodes: Sequence[str]) -> None:
        """Initialize the options widget."""
        super().__init__(title, name)
        self.combo_transfermode = QComboBox()
        self.combo_transfermode.addItems(transfermodes)
        self.spin_max_per_dir = QSpinBox()
        self.spin_max_per_dir.setSpecialValueText("Unlimited")
        self.chk_unique_folders = QCheckBox()
        self.chk_follow_symlink = QCheckBox()
        self.lineedit_rng_seed = QLineEdit(placeholderText="RNG Seed (optional)", clearButtonEnabled=True)
        set_qt_tips(self.combo_transfermode, "Select the transfer mode to use.")
        set_qt_tips(self.spin_max_per_dir, "Maximum number of files allowed per input folder. 0 for unlimited.")
        set_qt_tips(self.chk_unique_folders, "If checked, created folder names will have unique files.")
        set_qt_tips(self.chk_follow_symlink, "If checked, symbolic links will be followed during file traversal.")
        set_qt_tips(self.lineedit_rng_seed, "Seed for random number generator. If empty, system clock used.")
        layout = QFormLayout(self)
        layout.addRow("Transfer mode", self.combo_transfermode)
        layout.addRow("Max from one directory", self.spin_max_per_dir)
        layout.addRow("Ensure unique directories", self.chk_unique_folders)
        layout.addRow("Follow symbolic links", self.chk_follow_symlink)
        layout.addRow("Random seed", self.lineedit_rng_seed)

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        return {
            self.name: {
                "transfer_mode": self.combo_transfermode.currentText(),
                "max_per_dir": self.spin_max_per_dir.value(),
                "is_create_unique_dirs": self.chk_unique_folders.isChecked(),
                "should_follow_symlink": self.chk_follow_symlink.isChecked(),
                "rng_seed": self.lineedit_rng_seed.text(),
            },
        }

    def restore(self, config: dict) -> None:
        """Restore the options widget from config data."""
        c = self._section(config)
        self.combo_transfermode.setCurrentText(c.get("transfer_mode", TransferMode.DRY_RUN))
        self.spin_max_per_dir.setValue(c.get("max_per_dir", 0))
        self.chk_unique_folders.setChecked(c.get("is_create_unique_dirs", False))
        self.chk_follow_symlink.setChecked(c.get("should_follow_symlink", False))
        self.lineedit_rng_seed.setText(c.get("rng_seed", ""))


@cache
def get_component_map() -> Sequence[
    tuple[type[BaseGroupBox], str, str] | tuple[type[BaseGroupBox], str, str, Sequence[str]]
]:
    """Get the mapping of config sections to component classes and their init args."""
    return (
        (PathSelectorWidget, "Root", "root"),
        (PathSelectorWidget, "Destination", "dest"),
        (FileCountWidget, "File count", "filecount"),
        (DirectoryCreateWidget, "Create directories", "directory"),
        (FilenamerWidget, "Filenamer", "filename"),
        (TextFilterWidget, "Directory names", "dirname"),
        (TextFilterWidget, "Keywords", "keyword"),
        (TextFilterWidget, "Extensions", "extension"),
        (RangeFilterWidget, "File size", "filesize", tuple(SIZE_MAP.keys())),
        (RangeFilterWidget, "Duration", "duration", tuple(TIME_MAP.keys())),
        (OptionsWidget, "Options", "options", available_transfer_fns()),
    )


class LogWidget(QTextBrowser):
    """Logging text box."""

    def __init__(self) -> None:
        """Initialize the log widget."""
        super().__init__()
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        set_qt_tips(self, "Log for output messages.")


class ProgressWidget(QWidget):
    """Progress bars."""

    def __init__(self) -> None:
        """Initialize the progress widget."""
        super().__init__()
        self.progbar_dirs = QProgressBar(textVisible=True)
        self.progbar_files = QProgressBar(textVisible=True)
        set_qt_tips(self.progbar_dirs, "Total progress bar, max is set at number of output folders.")
        set_qt_tips(self.progbar_files, "Current folder progress bar, max is set at number of files to copy.")
        layout = QFormLayout(self)
        layout.addRow("Directories", self.progbar_dirs)
        layout.addRow("Files", self.progbar_files)

    def handle_start_process(self, dir_count: int) -> None:
        """Set up the progress bars at the start of the process."""
        self.progbar_dirs.setMaximum(dir_count)
        self.progbar_dirs.setValue(0)
        self.progbar_files.setMaximum(0)
        self.progbar_files.setValue(0)

    def handle_directory_start(self, target: int) -> None:
        """Update the directory progress bar."""
        curr = self.progbar_dirs.value()
        self.progbar_dirs.setValue(curr + 1)
        self.progbar_files.setMaximum(target)
        self.progbar_files.setValue(0)

    def handle_file_transfer(self) -> None:
        """Update the file progress bar."""
        self.progbar_files.setValue(self.progbar_files.value() + 1)

    @property
    def file_percentage(self) -> int:
        """Calculate the current file progress percentage."""
        maximum = self.progbar_files.maximum()
        if maximum <= 0:
            return 0
        return int(self.progbar_files.value() * 100 / maximum)
