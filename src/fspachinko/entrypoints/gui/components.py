"""GUI components in PySide6."""

from os.path import exists, isdir
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QUrl, SignalInstance, Slot
from PySide6.QtGui import QDesktopServices
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
    QWidget,
)

from fspachinko.adapters.transfer import available_transfer_fns
from fspachinko.entrypoints.gui.helpers import get_qt_icon, set_qt_tips
from fspachinko.fp import Fp

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from PySide6.QtGui import QDragEnterEvent, QDropEvent


def connect_signals(*signals: tuple[SignalInstance, Callable]) -> None:
    """Wire up any custom signals/slots."""
    for signal_set in signals:
        signal, slot = signal_set
        signal.connect(slot)


def set_tips(*tips: tuple[QWidget, str]) -> None:
    """Set tooltips for all widgets based on TIPS_SPEC."""
    for tip_set in tips:
        widget, tip = tip_set
        set_qt_tips(widget, tip)


class BaseGroupBox(QGroupBox):
    """Base class for group boxes with common functionality."""

    def __init__(self, title: str, name: str, *, checkable: bool = False) -> None:
        """Initialize the base group box."""
        super().__init__()
        self.setObjectName(name)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setTitle(title)
        self.setCheckable(checkable)
        self.setFlat(True)
        self._getters = ()
        self._setters = ()

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        return {self.objectName(): {key: getter() for getter, key in self._getters}}

    def restore(self, config: dict) -> None:
        """Restore the widget from config data."""
        _sect = config.get(self.objectName(), {})
        for setter, key, fallback in self._setters:
            setter(_sect.get(key, fallback))


class PathSelectorWidget(BaseGroupBox):
    """Handles logic for selecting a path."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the path selector widget."""
        super().__init__(title, name)
        self.lbl_selected = QLabel()
        self.btn_browse = QPushButton(get_qt_icon("folder_open_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"), "")
        self.btn_open = QPushButton(get_qt_icon("open_in_new_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"), "")
        self._getters = ((self.lbl_selected.text, "path"),)
        self._setters = ((self.lbl_selected.setText, "path", ""),)
        set_tips(
            (self.lbl_selected, "Currently selected folder"),
            (self.btn_browse, "Browse"),
            (self.btn_open, "Open in file explorer"),
        )
        connect_signals(
            (self.btn_browse.clicked, self.browse),
            (self.btn_open.clicked, self.open),
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.addWidget(self.lbl_selected, 1)
        layout.addWidget(self.btn_browse)
        layout.addWidget(self.btn_open)
        self.setAcceptDrops(True)

    @Slot()
    def browse(self) -> None:
        """Return the browse button."""
        d = QFileDialog.getExistingDirectory(
            dir=self.lbl_selected.text(),
            caption=f"Select {self.title()}",
        )
        if d:
            self.lbl_selected.setText(d)

    @Slot()
    def open(self) -> None:
        """Open the currently selected path in file explorer."""
        path = self.lbl_selected.text()
        if not path or not exists(path):
            msg = f"Cannot open {self.title()} folder. No valid path selected."
            raise FileNotFoundError(msg)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        """Handle drag enter event for folder paths."""
        if event.mimeData().hasFormat("text/uri-list"):
            for url in event.mimeData().urls():
                if isdir(url.toLocalFile()):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """Handle drop event for folder paths."""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if isdir(path):
                self.lbl_selected.setText(path)
                return


class FileCountWidget(BaseGroupBox):
    """Handles logic for file count settings."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the file count widget."""
        super().__init__(title, name)
        self.radio_fixed = QRadioButton("Fixed")
        self.spin_fixed = QSpinBox(minimum=1, maximum=Fp.MAXINT)
        self.radio_rand = QRadioButton("Random")
        self.spin_min_rand = QSpinBox(minimum=1, maximum=Fp.MAXINT)
        self.spin_max_rand = QSpinBox(minimum=2, maximum=Fp.MAXINT)
        self._getters = (
            (self.radio_rand.isChecked, "is_rand_enabled"),
            (self.spin_fixed.value, "count"),
            (self.spin_min_rand.value, "rand_min"),
            (self.spin_max_rand.value, "rand_max"),
        )
        self._setters = (
            (lambda rand: self.radio_fixed.setChecked(not rand), "is_rand_enabled", False),
            (lambda rand: self.spin_fixed.setEnabled(not rand), "is_rand_enabled", False),
            (self.radio_rand.setChecked, "is_rand_enabled", False),
            (self.spin_min_rand.setEnabled, "is_rand_enabled", False),
            (self.spin_max_rand.setEnabled, "is_rand_enabled", False),
            (self.spin_fixed.setValue, "count", 1),
            (self.spin_min_rand.setValue, "rand_min", 1),
            (self.spin_max_rand.setValue, "rand_max", 10),
        )
        set_tips(
            (self.radio_fixed, "Select fixed file count"),
            (self.spin_fixed, "Number of files to copy"),
            (self.radio_rand, "Select random file count"),
            (self.spin_min_rand, "Minimum random file count"),
            (self.spin_max_rand, "Maximum random file count"),
        )
        connect_signals(
            (self.radio_fixed.toggled, self.spin_fixed.setEnabled),
            (self.radio_rand.toggled, self.spin_min_rand.setEnabled),
            (self.radio_rand.toggled, self.spin_max_rand.setEnabled),
            (self.spin_min_rand.valueChanged, self.spin_max_rand.setMinimum),
            (self.spin_max_rand.valueChanged, self.spin_min_rand.setMaximum),
        )
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.addWidget(self.radio_fixed, 0, 0)
        layout.addWidget(self.radio_rand, 1, 0)
        layout.addWidget(self.spin_fixed, 0, 1)
        layout.addWidget(self.spin_min_rand, 1, 1)
        layout.addWidget(self.spin_max_rand, 2, 1)


class DirectoryCreateWidget(BaseGroupBox):
    """Handles logic for creating folders."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the create folders widget."""
        super().__init__(title, name, checkable=True)
        self.spinbox_folder_count = QSpinBox(minimum=1, maximum=Fp.MAXINT)
        self.lineedit_folder_name = QLineEdit(placeholderText="Ex: Random_Files", clearButtonEnabled=True)
        self._getters = (
            (self.isChecked, "is_enabled"),
            (self.spinbox_folder_count.value, "count"),
            (self.lineedit_folder_name.text, "name"),
        )
        self._setters = (
            (self.setChecked, "is_enabled", False),
            (self.spinbox_folder_count.setValue, "count", 1),
            (self.lineedit_folder_name.setText, "name", "fsp_output"),
        )
        set_tips(
            (self.spinbox_folder_count, "Number of folders to create"),
            (self.lineedit_folder_name, "Template for naming created folders"),
        )
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.addRow("Count:", self.spinbox_folder_count)
        layout.addRow("Name:", self.lineedit_folder_name)


class FilenamerWidget(BaseGroupBox):
    """Handles logic for filename template settings."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the filename template settings widget."""
        super().__init__(title, name, checkable=True)
        self.lineedit_template = QLineEdit(
            placeholderText=f"Ex: {Fp.FilenameTemplate.ORIGINAL}_{Fp.FilenameTemplate.INDEX}",
            clearButtonEnabled=True,
        )
        self.menu = QMenu()
        self.btn_insert = QPushButton("Insert tag")
        self.btn_insert.setMenu(self.menu)
        for lbl in Fp.FilenameTemplate:
            action = self.menu.addAction(lbl)
            action.triggered.connect(lambda _, tag=lbl: self.insert_tag(tag))
        self._getters = (
            (self.isChecked, "is_enabled"),
            (self.lineedit_template.text, "template"),
        )
        self._setters = (
            (self.setChecked, "is_enabled", False),
            (self.lineedit_template.setText, "template", Fp.FilenameTemplate.ORIGINAL),
        )
        set_tips(
            (self.lineedit_template, "File rename template, use 'Insert tag' button to add tags"),
            (self.btn_insert, "Insert tag into template at cursor position"),
            (self.menu, "Select tag to insert into template"),
        )
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.addRow("Template:", self.lineedit_template)
        layout.addRow("Tags:", self.btn_insert)

    @Slot(str)
    def insert_tag(self, tag: str) -> None:
        """Insert a tag into the template at the cursor position."""
        self.lineedit_template.insert(tag)
        self.lineedit_template.setFocus()


class TextFilterWidget(BaseGroupBox):
    """Handles the Include/Exclude text pattern."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the dual list widget."""
        super().__init__(title, name, checkable=True)
        self.lineedit_filter = QLineEdit(placeholderText="comma,separated,items", clearButtonEnabled=True)
        self.radio_include = QRadioButton("Include")
        self.radio_exclude = QRadioButton("Exclude")
        self._getters = (
            (self.isChecked, "is_enabled"),
            (self.lineedit_filter.text, "text"),
            (self.radio_include.isChecked, "should_include"),
        )
        self._setters = (
            (self.setChecked, "is_enabled", False),
            (self.lineedit_filter.setText, "text", ""),
            (self.radio_include.setChecked, "should_include", True),
        )
        set_tips(
            (self.lineedit_filter, "Enter items separated by commas"),
            (self.radio_include, "Include only items matching filter"),
            (self.radio_exclude, "Exclude any items matching filter"),
        )
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.addWidget(self.lineedit_filter, 0, 0, 1, 2)
        layout.addWidget(self.radio_include, 1, 0)
        layout.addWidget(self.radio_exclude, 1, 1)


class RangeFilterWidget(BaseGroupBox):
    """Handles logic for ranges (min/max), e.g., Size or Duration."""

    def __init__(self, title: str, name: str, items: Sequence[str]) -> None:
        """Initialize the range filter widget."""
        super().__init__(title, name, checkable=True)
        self.spin_min = QDoubleSpinBox(minimum=0.0, maximum=Fp.MAXFLOAT)
        self.spin_max = QDoubleSpinBox(minimum=0.0, maximum=Fp.MAXFLOAT)
        self.combo_unit = QComboBox()
        self.combo_unit.addItems(items)
        self._getters = (
            (self.isChecked, "is_enabled"),
            (self.spin_min.value, "minimum"),
            (self.spin_max.value, "maximum"),
            (self.combo_unit.currentText, "unit"),
        )
        self._setters = (
            (self.setChecked, "is_enabled", False),
            (self.spin_min.setValue, "minimum", 0.0),
            (self.spin_max.setValue, "maximum", 10.0),
            (self.combo_unit.setCurrentText, "unit", items[0] if items else ""),
        )
        set_tips(
            (self.spin_min, "Minimum value"),
            (self.spin_max, "Maximum value"),
            (self.combo_unit, "Unit"),
        )
        connect_signals(
            (self.spin_min.valueChanged, self.spin_max.setMinimum),
            (self.spin_max.valueChanged, self.spin_min.setMaximum),
        )
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.addRow("Min:", self.spin_min)
        layout.addRow("Max:", self.spin_max)
        layout.addRow("Unit:", self.combo_unit)


class OptionsWidget(BaseGroupBox):
    """Handles logic for miscellaneous options."""

    def __init__(self, title: str, name: str, transfermodes: Sequence[str]) -> None:
        """Initialize the options widget."""
        super().__init__(title, name)
        self.combo_transfermode = QComboBox()
        self.combo_transfermode.addItems(transfermodes)
        self.chk_follow_symlink = QCheckBox()
        self.lineedit_rng_seed = QLineEdit(placeholderText="RNG Seed (optional)", clearButtonEnabled=True)
        self.spin_max_per_dir = QSpinBox(minimum=0, maximum=Fp.MAXINT)
        self.spin_max_per_dir.setSpecialValueText("Unlimited")
        self._getters = (
            (self.combo_transfermode.currentText, "transfer_mode"),
            (self.chk_follow_symlink.isChecked, "should_follow_symlink"),
            (self.lineedit_rng_seed.text, "rng_seed"),
            (self.spin_max_per_dir.value, "max_per_dir"),
        )
        self._setters = (
            (self.combo_transfermode.setCurrentText, "transfer_mode", Fp.TransferMode.DRY_RUN),
            (self.chk_follow_symlink.setChecked, "should_follow_symlink", False),
            (self.lineedit_rng_seed.setText, "rng_seed", ""),
            (self.spin_max_per_dir.setValue, "max_per_dir", 0),
        )
        set_tips(
            (self.combo_transfermode, "Select transfer mode"),
            (self.chk_follow_symlink, "If checked, symbolic links followed during file traversal"),
            (self.lineedit_rng_seed, "Seed for random number generator, system clock used if empty"),
            (self.spin_max_per_dir, "Maximum number of files allowed per input folder, 0 for unlimited"),
        )
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.addRow("Transfer mode:", self.combo_transfermode)
        layout.addRow("Follow symbolic links:", self.chk_follow_symlink)
        layout.addRow("RNG Seed:", self.lineedit_rng_seed)
        layout.addRow("Max from one directory:", self.spin_max_per_dir)


class MainConfigWidget(QWidget):
    """Main widget."""

    def __init__(self) -> None:
        """Initialize the main widget."""
        super().__init__()
        self._widgets: dict[str, BaseGroupBox] = {
            "root": PathSelectorWidget("Root", "root"),
            "dest": PathSelectorWidget("Destination", "dest"),
            "filecount": FileCountWidget("File count", "filecount"),
            "directory": DirectoryCreateWidget("Create directories", "directory"),
            "filename": FilenamerWidget("Filenamer", "filename"),
            "dirname": TextFilterWidget("Directory names", "dirname"),
            "keyword": TextFilterWidget("Keywords", "keyword"),
            "extension": TextFilterWidget("Extensions", "extension"),
            "filesize": RangeFilterWidget("File size", "filesize", tuple(Fp.SIZE_MAP.keys())),
            "duration": RangeFilterWidget("Duration", "duration", tuple(Fp.TIME_MAP.keys())),
            "options": OptionsWidget("Options", "options", available_transfer_fns()),
        }
        layout = QGridLayout(self)
        layout.setContentsMargins(25, 5, 25, 5)
        layout.setColumnMinimumWidth(0, 256)
        layout.setColumnMinimumWidth(1, 256)
        layout.setColumnMinimumWidth(2, 256)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)
        layout.addWidget(self._widgets["root"], 0, 0, 1, 3)
        layout.addWidget(self._widgets["dest"], 1, 0, 1, 3)
        layout.addWidget(self._widgets["filecount"], 2, 0)
        layout.addWidget(self._widgets["directory"], 2, 1)
        layout.addWidget(self._widgets["filename"], 2, 2)
        layout.addWidget(self._widgets["dirname"], 3, 0)
        layout.addWidget(self._widgets["keyword"], 3, 1)
        layout.addWidget(self._widgets["extension"], 3, 2)
        layout.addWidget(self._widgets["filesize"], 4, 0)
        layout.addWidget(self._widgets["duration"], 4, 1)
        layout.addWidget(self._widgets["options"], 4, 2)

    @property
    def config(self) -> dict:
        """Capture the current configuration from the UI."""
        return {k: v for w in self._widgets.values() for k, v in w.config.items()}

    def restore(self, config: dict) -> None:
        """Restore the configuration to the UI."""
        for w in self._widgets.values():
            w.restore(config)

    def toggle(self, *, is_enabled: bool) -> None:
        for w in self._widgets.values():
            w.setEnabled(is_enabled)


class BaseDockWidget(QDockWidget):
    """Base class for dock widgets with common functionality."""

    def __init__(self, title: str, name: str, w: QWidget, parent: QWidget | None = None) -> None:
        """Initialize the base dock widget."""
        super().__init__(title, parent)
        self.setObjectName(name)
        self.setWidget(w)
        f = QDockWidget.DockWidgetFeature
        self.setFeatures(f.DockWidgetMovable | f.DockWidgetFloatable)


class LogWidget(QTextBrowser):
    """Logging text box."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the log widget."""
        super().__init__(parent)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        set_tips((self, "Log for output messages."))


class ProgressWidget(QWidget):
    """Progress bars."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the progress widget."""
        super().__init__(parent)
        self.progbar_dirs = QProgressBar(textVisible=True)
        self.progbar_files = QProgressBar(textVisible=True)
        set_tips(
            (self.progbar_dirs, "Total progress bar, max is set at number of output folders."),
            (self.progbar_files, "Current folder progress bar, max is set at number of files to copy."),
        )
        layout = QFormLayout(self)
        layout.addRow("Dirs", self.progbar_dirs)
        layout.addRow("Files", self.progbar_files)

    @property
    def file_percentage(self) -> int:
        """Calculate the current file progress percentage."""
        maximum = self.progbar_files.maximum()
        if maximum <= 0:
            return 0
        return int(self.progbar_files.value() * 100 / maximum)

    def handle_start_process(self, dir_count: int) -> None:
        """Set up the progress bars at the start of the process."""
        self.progbar_dirs.setMaximum(dir_count)
        self.progbar_dirs.setValue(0)
        self.progbar_files.setMaximum(Fp.MAXINT)
        self.progbar_files.setValue(0)

    def handle_directory_start(self, target: int) -> None:
        """Update the directory progress bar."""
        curr = self.progbar_dirs.value()
        self.progbar_dirs.setValue(curr + 1)
        self.progbar_files.setMaximum(target)
        self.progbar_files.setValue(0)

    def handle_file_transfer(self) -> None:
        """Update the file progress bar."""
        curr = self.progbar_files.value()
        self.progbar_files.setValue(curr + 1)
