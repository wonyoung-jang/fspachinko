"""GUI components in PySide6 for File Roulette."""

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from PySide6.QtCore import QDir, QObject, QUrl, Signal, Slot
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
    FilecountModel,
    FilenameModel,
    FolderModel,
    ListIncludeExcludeModel,
    MinMaxModel,
    OptionsModel,
    SizeLimitModel,
    TransferModeModel,
)
from ..core import get_available_transfer_modes
from ..utils import (
    SIZE_MAP,
    TIME_MAP,
    ByteUnit,
    FilenameTemplate,
    IconFilename,
    Paths,
    TimeUnit,
    TransferMode,
    convert_string_to_list,
)
from .qthelpers import set_qt_name, set_qt_tips

if TYPE_CHECKING:
    from collections.abc import Sequence

    from PySide6.QtGui import QDragEnterEvent, QDropEvent

    from .workers import WorkerSignals

logger = logging.getLogger(__name__)


class BaseGroupBox(QGroupBox):
    """Base class for group boxes with common functionality."""

    def __init__(self, title: str, name: str, *, parent: QWidget | None = None, checkable: bool = False) -> None:
        """Initialize the base group box."""
        super().__init__(title=title, parent=parent)
        set_qt_name(self, name)
        self.setCheckable(checkable)


class PathSelectorWidget(BaseGroupBox):
    """Handles logic for selecting a path."""

    def __init__(self, title: str, name: str, items: Sequence[str], parent: QWidget | None = None) -> None:
        """Initialize the path selector widget."""
        super().__init__(title, name, parent=parent)
        self.setAcceptDrops(True)

        title_lower = self.title().casefold()

        self.combo = QComboBox()
        self.combo.addItems(items)
        set_qt_name(self.combo, f"{name}_combo")
        set_qt_tips(self.combo, f"Select or enter a path for {title_lower}.")

        icon_browse = QIcon(Paths.icon(IconFilename.BROWSE))
        icon_open = QIcon(Paths.icon(IconFilename.OPEN_DIR))
        icon_delete = QIcon(Paths.icon(IconFilename.REMOVE))

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

        self.btn_delete = QPushButton()
        self.btn_delete.setIcon(icon_delete)
        self.btn_delete.clicked.connect(self.delete_curr_item)
        set_qt_name(self.btn_delete, f"{name}_delete_btn")
        set_qt_tips(self.btn_delete, f"Delete current {title_lower} entry.")

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
            if os.path.isdir(path):
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
        if self.combo.count() > 0:
            self.combo.removeItem(self.combo.currentIndex())

    @Slot()
    def open(self) -> None:
        """Open the currently selected path in file explorer."""
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.combo.currentText()))
        except Exception:
            logger.exception("Failed to open path")

    def get_config(self) -> str:
        """Return clean data for the config."""
        return os.path.realpath(self.combo.currentText())


class RootPathSelectorWidget(PathSelectorWidget):
    """Handles logic for selecting a root path."""

    def __init__(self) -> None:
        """Initialize the root path selector widget."""
        super().__init__("Root", "root", [QDir.rootPath()])


class DestPathSelectorWidget(PathSelectorWidget):
    """Handles logic for selecting a destination path."""

    def __init__(self) -> None:
        """Initialize the destination path selector widget."""
        super().__init__("Destination", "dest", [QDir.homePath()])


class FileCountWidget(BaseGroupBox):
    """Handles logic for file count settings."""

    def __init__(self, title: str = "File count", name: str = "filecount", parent: QWidget | None = None) -> None:
        """Initialize the file count widget."""
        super().__init__(title, name, parent=parent)

        self.radio_fixed = QRadioButton("Fixed")
        self.radio_fixed.setChecked(True)
        set_qt_name(self.radio_fixed, f"{name}_fixed_chk")
        set_qt_tips(self.radio_fixed, "Select fixed file count.")

        self.spin_fixed = QSpinBox(suffix=" files")
        set_qt_name(self.spin_fixed, f"{name}_fixed_val")
        set_qt_tips(self.spin_fixed, "Number of files to copy.")

        self.radio_rand = QRadioButton("Random")
        set_qt_name(self.radio_rand, f"{name}_rand_chk")
        set_qt_tips(self.radio_rand, "Select random file count.")

        self.spin_min_rand = QSpinBox(prefix="Min: ")
        set_qt_name(self.spin_min_rand, f"{name}_rand_min")
        set_qt_tips(self.spin_min_rand, "Minimum random file count.")

        self.spin_max_rand = QSpinBox(prefix="Max: ")
        set_qt_name(self.spin_max_rand, f"{name}_rand_max")
        set_qt_tips(self.spin_max_rand, "Maximum random file count.")

        self.spin_min_rand.valueChanged.connect(self.spin_max_rand.setMinimum)
        self.spin_max_rand.valueChanged.connect(self.spin_min_rand.setMaximum)

        self.radio_fixed.toggled.connect(self.spin_fixed.setEnabled)
        self.radio_fixed.toggled.connect(lambda c: self.spin_min_rand.setDisabled(c))
        self.radio_fixed.toggled.connect(lambda c: self.spin_max_rand.setDisabled(c))

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
            rand_enabled=self.radio_rand.isChecked(),
            rand_min=self.spin_min_rand.value(),
            rand_max=self.spin_max_rand.value(),
        )


class FolderCreatorWidget(BaseGroupBox):
    """Handles logic for creating folders."""

    def __init__(self, title: str = "Create Folders", name: str = "folder", parent: QWidget | None = None) -> None:
        """Initialize the create folders widget."""
        super().__init__(title, name, parent=parent, checkable=True)

        self.spinbox_folder_count = QSpinBox(suffix=" folders")
        set_qt_name(self.spinbox_folder_count, f"{name}_count")
        set_qt_tips(self.spinbox_folder_count, "Number of folders to create.")

        self.lineedit_folder_name = QLineEdit(placeholderText="Ex: Random_Files", clearButtonEnabled=True)
        set_qt_name(self.lineedit_folder_name, f"{name}_name")
        set_qt_tips(self.lineedit_folder_name, "Template for naming created folders.")

        self.chk_unique_folders = QCheckBox("Ensure unique folders")
        self.chk_unique_folders.setChecked(True)
        set_qt_name(self.chk_unique_folders, f"{name}_unique")
        set_qt_tips(self.chk_unique_folders, "If checked, created folder names will have unique files.")

        layout = QVBoxLayout(self)
        layout.addWidget(self.spinbox_folder_count)
        layout.addWidget(self.lineedit_folder_name)
        layout.addWidget(self.chk_unique_folders)

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

        self.edit_template = QLineEdit("{original}", placeholderText="Ex: {original}_{index}", clearButtonEnabled=True)
        set_qt_name(self.edit_template, f"{name}_template")
        set_qt_tips(
            self.edit_template,
            "Template for renaming files. Use the 'Insert Tag' button to add tags.",
        )

        self.btn_template = QPushButton("Insert tag")
        set_qt_name(self.btn_template, f"{name}_template_button")
        set_qt_tips(self.btn_template, "Insert a tag into the template at the cursor position.")

        self.menu_template = QMenu("Tags", self)
        set_qt_name(self.menu_template, f"{name}_template_menu")
        set_qt_tips(self.menu_template, "Select a tag to insert into the filename template.")

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
        val = self.edit_template.text() or "{original}"
        return FilenameModel(template=val)


class TransferModeWidget(BaseGroupBox):
    """Handles logic for mode settings."""

    def __init__(self, title: str = "Transfer Mode", name: str = "transfermode", parent: QWidget | None = None) -> None:
        """Initialize the mode settings widget."""
        super().__init__(title, name, parent=parent)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(get_available_transfer_modes())
        set_qt_name(self.combo_mode, f"{name}_mode")
        set_qt_tips(self.combo_mode, "Select the transfer mode to use.")

        layout = QVBoxLayout(self)
        layout.addWidget(self.combo_mode)

    def get_config(self) -> TransferModeModel:
        """Return clean data for the config."""
        return TransferModeModel(transfer_mode=TransferMode(self.combo_mode.currentText()))


class DualListFilterWidget(BaseGroupBox):
    """Handles the Include/Exclude pattern for Keywords and Extensions."""

    def __init__(self, title: str, name: str, parent: QWidget | None = None) -> None:
        """Initialize the dual list widget."""
        super().__init__(title, name, parent=parent)

        self.filter_edit = QLineEdit(placeholderText="comma,separated,items", clearButtonEnabled=True)
        set_qt_name(self.filter_edit, f"{name}_text")
        set_qt_tips(self.filter_edit, f"Enter {title.lower()} separated by commas.")

        self.filter_include_radio = QRadioButton("Include")
        self.filter_include_radio.setChecked(True)
        set_qt_name(self.filter_include_radio, f"{name}_include")
        set_qt_tips(self.filter_include_radio, f"Include only items matching the {title.lower()} filter.")

        self.filter_exclude_radio = QRadioButton("Exclude")
        set_qt_name(self.filter_exclude_radio, f"{name}_exclude")
        set_qt_tips(self.filter_exclude_radio, f"Exclude items matching the {title.lower()} filter.")

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


class ExtensionsFilterWidget(DualListFilterWidget):
    """Handles the Include/Exclude pattern for file extensions."""

    def __init__(self) -> None:
        """Initialize the extensions filter widget."""
        super().__init__("Extensions", "extension")


class KeywordsFilterWidget(DualListFilterWidget):
    """Handles the Include/Exclude pattern for keywords."""

    def __init__(self) -> None:
        """Initialize the keywords filter widget."""
        super().__init__("Keywords", "keyword")


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

        self.min_spin = QDoubleSpinBox(prefix="Min: ")
        set_qt_name(self.min_spin, f"{name}_minimum")
        set_qt_tips(self.min_spin, f"Minimum value for the {name} filter.")

        self.max_spin = QDoubleSpinBox(prefix="Max: ")
        set_qt_name(self.max_spin, f"{name}_maximum")
        set_qt_tips(self.max_spin, f"Maximum value for the {name} filter.")

        self.min_spin.valueChanged.connect(self.max_spin.setMinimum)
        self.max_spin.valueChanged.connect(self.min_spin.setMaximum)

        self.combo = QComboBox()
        self.combo.addItems(items)
        set_qt_name(self.combo, f"{name}_unit")
        set_qt_tips(self.combo, f"Unit multiplier for the {name} filter.")

        layout = QHBoxLayout(self)
        layout.addWidget(self.min_spin)
        layout.addWidget(self.max_spin)
        layout.addWidget(self.combo)

    def get_config(self) -> MinMaxModel:
        """Return clean data for the config."""
        mult = self.mapping.get(self.combo.currentText(), 1)
        minimum, maximum = self.min_spin.value() * mult, self.max_spin.value() * mult
        return MinMaxModel(enabled=self.isChecked(), minimum=minimum, maximum=maximum)


class SizeFilterWidget(DblRangeFilterWidget):
    """Handles logic for size range filter."""

    def __init__(self) -> None:
        """Initialize the size filter widget."""
        super().__init__("File Size", "filesize", tuple(ByteUnit), SIZE_MAP)


class DurationFilterWidget(DblRangeFilterWidget):
    """Handles logic for duration range filter."""

    def __init__(self) -> None:
        """Initialize the duration filter widget."""
        super().__init__("Duration", "duration", tuple(TimeUnit), TIME_MAP)


class SizeLimitWidget(BaseGroupBox):
    """Handles logic for output folder size limit."""

    def __init__(
        self,
        title: str,
        name: str,
        items: Sequence[str | ByteUnit | TimeUnit],
        mapping: dict[str | ByteUnit | TimeUnit, int],
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the size limit widget."""
        super().__init__(title, name, parent=parent, checkable=True)

        self.mapping = mapping

        self.size_spin = QDoubleSpinBox(prefix="Size: ")
        self.size_spin.setSpecialValueText("Unlimited")
        set_qt_name(self.size_spin, f"{name}_size")
        set_qt_tips(self.size_spin, f"{title} value for the size limit.")

        self.combo = QComboBox()
        self.combo.addItems(items)
        set_qt_name(self.combo, f"{name}_unit")
        set_qt_tips(self.combo, f"Unit multiplier for the {title} filter.")

        layout = QHBoxLayout(self)
        layout.addWidget(self.size_spin)
        layout.addWidget(self.combo)

    def get_config(self) -> SizeLimitModel:
        """Return clean data for the config."""
        mult = self.mapping.get(self.combo.currentText(), 1)
        size_limit = self.size_spin.value() * mult
        return SizeLimitModel(enabled=self.isChecked(), size_limit=size_limit)


class FolderSizeLimitWidget(SizeLimitWidget):
    """Handles logic for per-folder size limit."""

    def __init__(self) -> None:
        """Initialize the folder size limit widget."""
        super().__init__("Max Folder Size", "folder_size_limit", tuple(ByteUnit), SIZE_MAP)


class TotalSizeLimitWidget(SizeLimitWidget):
    """Handles logic for total size limit across all folders."""

    def __init__(self) -> None:
        """Initialize the total size limit widget."""
        super().__init__("Max Total Size", "total_size_limit", tuple(ByteUnit), SIZE_MAP)


class ProgressWidget(QWidget):
    """Progress bars and execution controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the execution widget."""
        super().__init__(parent=parent)

        self.progbar_total = QProgressBar(textVisible=True)
        set_qt_name(self.progbar_total, "progress_total")
        set_qt_tips(self.progbar_total, "Total progress bar, max is set at number of output folders.")

        self.progbar_folder = QProgressBar(textVisible=True)
        set_qt_name(self.progbar_folder, "progress_folder")
        set_qt_tips(self.progbar_folder, "Current folder progress bar, max is set at number of files to copy.")

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

    def __init__(self, name: str = "logging", parent: QWidget | None = None) -> None:
        """Initialize the logging widget."""
        super().__init__(parent=parent)
        set_qt_name(self, name)

        self.textbrowser_log = QTextBrowser()
        self.textbrowser_log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        set_qt_name(self.textbrowser_log, f"{name}_log")
        set_qt_tips(self.textbrowser_log, "Log for output messages.")

        layout = QHBoxLayout(self)
        layout.addWidget(self.textbrowser_log)


class OptionsWidget(BaseGroupBox):
    """Handles logic for miscellaneous options."""

    def __init__(self, title: str = "Options", name: str = "options", parent: QWidget | None = None) -> None:
        """Initialize the options widget."""
        super().__init__(title, name, parent=parent)

        self.spin_max_per_folder = QSpinBox()
        self.spin_max_per_folder.setSpecialValueText("Unlimited")
        set_qt_name(self.spin_max_per_folder, f"{name}_max_per_folder")
        set_qt_tips(self.spin_max_per_folder, "Maximum number of files allowed per input folder. 0 for unlimited.")

        self.chk_follow_symlinks = QCheckBox()
        set_qt_name(self.chk_follow_symlinks, f"{name}_follow_symlinks")
        set_qt_tips(self.chk_follow_symlinks, "If checked, symbolic links will be followed during file traversal.")

        self.chk_dry_run = QCheckBox()
        set_qt_name(self.chk_dry_run, f"{name}_dry_run")
        set_qt_tips(self.chk_dry_run, "If checked, no files will actually be copied.")

        layout = QFormLayout(self)
        layout.addRow("Max from one folder", self.spin_max_per_folder)
        layout.addRow("Follow symbolic links", self.chk_follow_symlinks)
        layout.addRow("Dry run (simulation)", self.chk_dry_run)

    def get_config(self) -> OptionsModel:
        """Return clean data for the config."""
        return OptionsModel(
            max_per_folder=self.spin_max_per_folder.value(),
            follow_symlinks=self.chk_follow_symlinks.isChecked(),
            dry_run_enabled=self.chk_dry_run.isChecked(),
        )


@dataclass(slots=True)
class ProgressBinder(QObject):
    """Class for binding progress widgets."""

    progress: ProgressWidget
    logging: LoggingWidget

    count: ClassVar[Signal] = Signal(int)
    finished: ClassVar[Signal] = Signal()

    def __post_init__(self) -> None:
        """Initialize the ProgressBinder."""
        super().__init__()

    def bind(self, signals: WorkerSignals) -> None:
        """Bind worker signals to progress widget."""
        signals.progress_total.connect(self.progress.progbar_total.setMaximum)
        signals.count_total.connect(self.progress.update_total_prog)
        signals.progress.connect(self.progress.progbar_folder.setMaximum)
        signals.log.connect(self.logging.textbrowser_log.append)
        signals.count.connect(self.on_count)
        signals.finished.connect(self.finished.emit)

    @Slot(int)
    def on_count(self, count: int) -> None:
        """Handle folder progress count update."""
        self.progress.progbar_folder.setValue(count)
        self.count.emit(count)
