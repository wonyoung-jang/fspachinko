"""GUI components in PySide6."""

import logging
import os
from typing import TYPE_CHECKING

from PySide6.QtCore import QUrl, Signal, Slot
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

from ..core import (
    ByteUnit,
    DirectoryModel,
    FilecountModel,
    FilenameModel,
    FilenameTemplate,
    IconFilename,
    ListIncludeExcludeModel,
    MinMaxModel,
    OptionsModel,
    TimeUnit,
    get_available_transfer_modes,
    get_icon_path,
)
from .qthelpers import set_qt_name, set_qt_tips

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PySide6.QtGui import QDragEnterEvent, QDropEvent

    from .workers import WorkerSignals

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

        title_lower = self.title().casefold()

        self.label = QLabel()
        set_qt_name(self.label, f"{name}_label")
        set_qt_tips(self.label, f"Select the {title_lower} folder.")

        icon_browse = QIcon(get_icon_path(IconFilename.BROWSE))
        icon_open = QIcon(get_icon_path(IconFilename.OPEN_DIR))

        self.btn_browse = QPushButton()
        self.btn_browse.setIcon(icon_browse)
        self.btn_browse.clicked.connect(self.browse)
        set_qt_name(self.btn_browse, f"{name}_browse_btn")
        set_qt_tips(self.btn_browse, f"Browse for {title_lower} folder.")

        self.btn_open = QPushButton()
        self.btn_open.setIcon(icon_open)
        self.btn_open.clicked.connect(self.open)
        set_qt_name(self.btn_open, f"{name}_open_btn")
        set_qt_tips(self.btn_open, f"Open current {title_lower} folder in file explorer.")

        layout = QHBoxLayout(self)
        layout.addWidget(self.label, stretch=1)
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
                self.label.setText(path)

    @Slot()
    def browse(self) -> None:
        """Return the browse button."""
        d = QFileDialog.getExistingDirectory(
            parent=self,
            caption=f"Select {self.title()}",
            dir=self.label.text(),
        )
        if d:
            self.label.setText(d)

    @Slot()
    def open(self) -> None:
        """Open the currently selected path in file explorer."""
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.label.text()))
        except Exception:
            logger.exception("Failed to open path %s", self.label.text())

    def get_config(self) -> str:
        """Return clean data for the config."""
        return self.label.text()


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


class FolderCreatorWidget(BaseGroupBox):
    """Handles logic for creating folders."""

    def __init__(self, title: str = "Create Folders", name: str = "folder") -> None:
        """Initialize the create folders widget."""
        super().__init__(title=title, name=name, checkable=True)

        self.spinbox_folder_count = QSpinBox(suffix=" folders", minimum=1)
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


class FilenameWidget(BaseGroupBox):
    """Handles logic for filename template settings."""

    def __init__(self, title: str = "Filename", name: str = "filename") -> None:
        """Initialize the filename template settings widget."""
        super().__init__(title=title, name=name)

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
        return FilenameModel(template=self.edit_template.text().strip() or "{original}")


class ListIncludeExcludeFilterWidget(BaseGroupBox):
    """Handles the Include/Exclude pattern for Keywords and Extensions."""

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

    def get_config(self) -> ListIncludeExcludeModel:
        """Return clean data for the config."""
        return ListIncludeExcludeModel(
            is_enabled=self.isChecked(),
            should_include=self.filter_include_radio.isChecked(),
            text=self.filter_edit.text(),
        )


class DirectoryFilterWidget(ListIncludeExcludeFilterWidget):
    """Handles the Include/Exclude pattern for directory names."""

    def __init__(self) -> None:
        """Initialize the directory filter widget."""
        super().__init__(title="Directory Name", name="directory_name_filter")


class ExtensionsFilterWidget(ListIncludeExcludeFilterWidget):
    """Handles the Include/Exclude pattern for file extensions."""

    def __init__(self) -> None:
        """Initialize the extensions filter widget."""
        super().__init__(title="Extensions", name="extension")


class KeywordsFilterWidget(ListIncludeExcludeFilterWidget):
    """Handles the Include/Exclude pattern for keywords."""

    def __init__(self) -> None:
        """Initialize the keywords filter widget."""
        super().__init__(title="Keywords", name="keyword")


class MinMaxFilterWidget(BaseGroupBox):
    """Handles logic for ranges (Min/Max), e.g., Size or Duration."""

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

    def get_config(self) -> MinMaxModel:
        """Return clean data for the config."""
        return MinMaxModel(
            is_enabled=self.isChecked(),
            minimum=self.spin_min.value(),
            maximum=self.spin_max.value(),
            unit=self.combo_unit.currentText(),
        )


class SizeFilterWidget(MinMaxFilterWidget):
    """Handles logic for size range filter."""

    def __init__(self) -> None:
        """Initialize the size filter widget."""
        super().__init__(title="File Size", name="filesize", items=tuple(ByteUnit))


class DurationFilterWidget(MinMaxFilterWidget):
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
        self.combo_mode.addItems(get_available_transfer_modes())
        set_qt_name(self.combo_mode, f"{name}_mode")
        set_qt_tips(self.combo_mode, "Select the transfer mode to use.")

        self.spin_max_per_folder = QSpinBox()
        self.spin_max_per_folder.setSpecialValueText("Unlimited")
        set_qt_name(self.spin_max_per_folder, f"{name}_max_per_folder")
        set_qt_tips(self.spin_max_per_folder, "Maximum number of files allowed per input folder. 0 for unlimited.")

        self.chk_follow_symlink = QCheckBox()
        set_qt_name(self.chk_follow_symlink, f"{name}_should_follow_symlink")
        set_qt_tips(self.chk_follow_symlink, "If checked, symbolic links will be followed during file traversal.")

        self.chk_dry_run = QCheckBox()
        set_qt_name(self.chk_dry_run, f"{name}_dry_run")
        set_qt_tips(self.chk_dry_run, "If checked, no files will actually be copied.")

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
        layout.addRow("Max from one folder", self.spin_max_per_folder)
        layout.addRow("Ensure unique folders", self.chk_unique_folders)
        layout.addRow("Follow symbolic links", self.chk_follow_symlink)
        layout.addRow("Dry run (simulation)", self.chk_dry_run)
        layout.addRow("RNG seed", self.rng_seed)

    def get_config(self) -> OptionsModel:
        """Return clean data for the config."""
        return OptionsModel(
            max_per_folder=self.spin_max_per_folder.value(),
            is_create_unique_folders=self.chk_unique_folders.isChecked(),
            should_follow_symlink=self.chk_follow_symlink.isChecked(),
            is_dry_run=self.chk_dry_run.isChecked(),
            rng_seed=self.rng_seed.text() or None,
        )


class ProgressWidget(QWidget):
    """Progress bars and execution controls."""

    count = Signal(int)
    finished = Signal()

    def __init__(self, name: str = "progress") -> None:
        """Post-initialize the progress widget."""
        super().__init__()
        set_qt_name(self, name)

        self.progbar_total = QProgressBar(textVisible=True)
        set_qt_name(self.progbar_total, f"{name}_total")
        set_qt_tips(self.progbar_total, "Total progress bar, max is set at number of output folders.")

        self.progbar_dir = QProgressBar(textVisible=True)
        set_qt_name(self.progbar_dir, f"{name}_dir")
        set_qt_tips(self.progbar_dir, "Current folder progress bar, max is set at number of files to copy.")

        layout = QFormLayout(self)
        layout.addRow("Total", self.progbar_total)
        layout.addRow("Folder", self.progbar_dir)

    def bind(self, signals: WorkerSignals) -> None:
        """Bind worker signals to progress widget."""
        signals.progress_total.connect(self.progbar_total.setMaximum)
        signals.count_total.connect(self.update_total_prog)
        signals.progress.connect(self.progbar_dir.setMaximum)
        signals.count.connect(self.on_count)
        signals.finished.connect(self.finished.emit)

    @Slot()
    def update_total_prog(self) -> None:
        """Update the total progress bar."""
        self.progbar_total.setValue(self.progbar_total.value() + 1)

    @Slot(int)
    def on_count(self, count: int) -> None:
        """Handle directory progress count update."""
        self.progbar_dir.setValue(count)
        self.count.emit(count)

    def reset(self) -> None:
        """Reset progress bars."""
        self.progbar_total.setValue(0)
        self.progbar_dir.setValue(0)


class LoggingWidget(QWidget):
    """Logging widget."""

    def __init__(self, name: str = "logging") -> None:
        """Post-initialize the logging widget."""
        super().__init__()
        set_qt_name(self, name)

        self.textbrowser_log = QTextBrowser()
        self.textbrowser_log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        set_qt_name(self.textbrowser_log, f"{name}_log")
        set_qt_tips(self.textbrowser_log, "Log for output messages.")

        layout = QHBoxLayout(self)
        layout.addWidget(self.textbrowser_log)
