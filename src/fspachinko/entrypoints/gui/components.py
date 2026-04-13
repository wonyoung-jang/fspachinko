"""GUI components in PySide6."""

from dataclasses import dataclass
from os.path import exists, isdir
from typing import TYPE_CHECKING, ClassVar

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
from fspachinko.constants import MAXIMUM_INT, SIZE_MAP, TIME_MAP, FilenameTemplate, TransferMode
from fspachinko.entrypoints.gui.helpers import get_qt_icon, set_qt_tips

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from PySide6.QtGui import QDragEnterEvent, QDropEvent


@dataclass(slots=True)
class SetupSpecs:
    """Specifications for setting up a component."""

    tips: Sequence[tuple[QWidget, str]] = ()
    getters: Sequence[tuple[Callable, str]] = ()
    setters: Sequence[tuple[Callable, str, object]] = ()
    signals: Sequence[tuple[SignalInstance, Callable]] = ()


class BaseGroupBox(QGroupBox):
    """Base class for group boxes with common functionality."""

    _specs: SetupSpecs

    def __init__(self, title: str, name: str, *, checkable: bool = False) -> None:
        """Initialize the base group box."""
        super().__init__()
        self.setObjectName(name)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setTitle(title)
        self.setCheckable(checkable)
        self.setFlat(True)
        self._wire_slots()
        self._set_tips()

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        config = {}
        for getter_set in self._specs.getters:
            getter, key = getter_set
            config[key] = getter()
        return {self.objectName(): config}

    def restore(self, config: dict) -> None:
        """Restore the widget from config data."""
        section = config.get(self.objectName(), {})
        for setter_set in self._specs.setters:
            setter, key, fallback = setter_set
            value = section.get(key, fallback)
            setter(value)

    def _wire_slots(self) -> None:
        """Wire up any custom signals/slots."""
        for signal_set in self._specs.signals:
            signal, slot = signal_set
            signal.connect(slot)

    def _set_tips(self) -> None:
        """Set tooltips for all widgets based on TIPS_SPEC."""
        for tip_set in self._specs.tips:
            widget, tip = tip_set
            set_qt_tips(widget, tip)


class PathSelectorWidget(BaseGroupBox):
    """Handles logic for selecting a path."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the path selector widget."""
        self.lbl_selected = QLabel()
        self.btn_browse = QPushButton(get_qt_icon("browse"), "")
        self.btn_open = QPushButton(get_qt_icon("open_dir"), "")
        self._specs = SetupSpecs(
            tips=(
                (self.lbl_selected, "Currently selected folder"),
                (self.btn_browse, "Browse"),
                (self.btn_open, "Open in file explorer"),
            ),
            getters=((self.lbl_selected.text, "path"),),
            setters=((self.lbl_selected.setText, "path", ""),),
            signals=(
                (self.btn_browse.clicked, self.browse),
                (self.btn_open.clicked, self.open),
            ),
        )
        super().__init__(title, name)
        layout = QHBoxLayout(self)
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
        self.radio_fixed = QRadioButton("Fixed")
        self.spin_fixed = QSpinBox(minimum=1, maximum=MAXIMUM_INT)
        self.radio_rand = QRadioButton("Random")
        self.spin_min_rand = QSpinBox(minimum=1, maximum=MAXIMUM_INT)
        self.spin_max_rand = QSpinBox(minimum=2, maximum=MAXIMUM_INT)
        self._specs = SetupSpecs(
            tips=(
                (self.radio_fixed, "Select fixed file count"),
                (self.spin_fixed, "Number of files to copy"),
                (self.radio_rand, "Select random file count"),
                (self.spin_min_rand, "Minimum random file count"),
                (self.spin_max_rand, "Maximum random file count"),
            ),
            getters=(
                (self.radio_rand.isChecked, "is_rand_enabled"),
                (self.spin_fixed.value, "count"),
                (self.spin_min_rand.value, "rand_min"),
                (self.spin_max_rand.value, "rand_max"),
            ),
            setters=(
                (lambda ire: self.radio_fixed.setChecked(not ire), "is_rand_enabled", False),
                (lambda ire: self.spin_fixed.setEnabled(not ire), "is_rand_enabled", False),
                (self.radio_rand.setChecked, "is_rand_enabled", False),
                (self.spin_min_rand.setEnabled, "is_rand_enabled", False),
                (self.spin_max_rand.setEnabled, "is_rand_enabled", False),
                (self.spin_fixed.setValue, "count", 1),
                (self.spin_min_rand.setValue, "rand_min", 1),
                (self.spin_max_rand.setValue, "rand_max", 10),
            ),
            signals=(
                (self.radio_fixed.toggled, self.spin_fixed.setEnabled),
                (self.radio_rand.toggled, self.spin_min_rand.setEnabled),
                (self.radio_rand.toggled, self.spin_max_rand.setEnabled),
                (self.spin_min_rand.valueChanged, self.spin_max_rand.setMinimum),
                (self.spin_max_rand.valueChanged, self.spin_min_rand.setMaximum),
            ),
        )
        super().__init__(title, name)
        layout = QGridLayout(self)
        layout.addWidget(self.radio_fixed, 0, 0)
        layout.addWidget(self.radio_rand, 1, 0)
        layout.addWidget(self.spin_fixed, 0, 1)
        layout.addWidget(self.spin_min_rand, 1, 1)
        layout.addWidget(self.spin_max_rand, 2, 1)


class DirectoryCreateWidget(BaseGroupBox):
    """Handles logic for creating folders."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the create folders widget."""
        self.spinbox_folder_count = QSpinBox(minimum=1, maximum=MAXIMUM_INT)
        self.lineedit_folder_name = QLineEdit(placeholderText="Ex: Random_Files", clearButtonEnabled=True)
        self._specs = SetupSpecs(
            tips=(
                (self.spinbox_folder_count, "Number of folders to create"),
                (self.lineedit_folder_name, "Template for naming created folders"),
            ),
            getters=(
                (self.isChecked, "is_enabled"),
                (self.spinbox_folder_count.value, "count"),
                (self.lineedit_folder_name.text, "name"),
            ),
            setters=(
                (self.setChecked, "is_enabled", False),
                (self.spinbox_folder_count.setValue, "count", 1),
                (self.lineedit_folder_name.setText, "name", "fsp_output"),
            ),
        )
        super().__init__(title, name, checkable=True)
        layout = QFormLayout(self)
        layout.addRow("Count:", self.spinbox_folder_count)
        layout.addRow("Name:", self.lineedit_folder_name)


class FilenamerWidget(BaseGroupBox):
    """Handles logic for filename template settings."""

    def __init__(self, title: str, name: str) -> None:
        """Initialize the filename template settings widget."""
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
        self._specs = SetupSpecs(
            tips=(
                (self.lineedit_template, "File rename template, use 'Insert tag' button to add tags"),
                (self.btn_insert, "Insert tag into template at cursor position"),
                (self.menu, "Select tag to insert into template"),
            ),
            getters=(
                (self.isChecked, "is_enabled"),
                (self.lineedit_template.text, "template"),
            ),
            setters=(
                (self.setChecked, "is_enabled", False),
                (self.lineedit_template.setText, "template", FilenameTemplate.ORIGINAL),
            ),
        )
        super().__init__(title, name, checkable=True)
        layout = QFormLayout(self)
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
        self.lineedit_filter = QLineEdit(placeholderText="comma,separated,items", clearButtonEnabled=True)
        self.radio_include = QRadioButton("Include")
        self.radio_exclude = QRadioButton("Exclude")
        self._specs = SetupSpecs(
            tips=(
                (self.lineedit_filter, "Enter items separated by commas"),
                (self.radio_include, "Include only items matching filter"),
                (self.radio_exclude, "Exclude any items matching filter"),
            ),
            getters=(
                (self.isChecked, "is_enabled"),
                (self.lineedit_filter.text, "text"),
                (self.radio_include.isChecked, "should_include"),
            ),
            setters=(
                (self.setChecked, "is_enabled", False),
                (self.lineedit_filter.setText, "text", ""),
                (self.radio_include.setChecked, "should_include", True),
            ),
        )
        super().__init__(title, name, checkable=True)
        layout = QGridLayout(self)
        layout.addWidget(self.lineedit_filter, 0, 0, 1, 2)
        layout.addWidget(self.radio_include, 1, 0)
        layout.addWidget(self.radio_exclude, 1, 1, Qt.AlignmentFlag.AlignLeft)


class RangeFilterWidget(BaseGroupBox):
    """Handles logic for ranges (min/max), e.g., Size or Duration."""

    def __init__(self, title: str, name: str, items: Sequence[str]) -> None:
        """Initialize the range filter widget."""
        self.spin_min = QDoubleSpinBox(minimum=0.0, maximum=float("inf"))
        self.spin_max = QDoubleSpinBox(minimum=0.0, maximum=float("inf"))
        self.combo_unit = QComboBox()
        self.combo_unit.addItems(items)
        self._specs = SetupSpecs(
            tips=(
                (self.spin_min, "Minimum value"),
                (self.spin_max, "Maximum value"),
                (self.combo_unit, "Unit"),
            ),
            getters=(
                (self.isChecked, "is_enabled"),
                (self.spin_min.value, "minimum"),
                (self.spin_max.value, "maximum"),
                (self.combo_unit.currentText, "unit"),
            ),
            setters=(
                (self.setChecked, "is_enabled", False),
                (self.spin_min.setValue, "minimum", 0.0),
                (self.spin_max.setValue, "maximum", 10.0),
                (self.combo_unit.setCurrentText, "unit", items[0] if items else ""),
            ),
            signals=(
                (self.spin_min.valueChanged, self.spin_max.setMinimum),
                (self.spin_max.valueChanged, self.spin_min.setMaximum),
            ),
        )
        super().__init__(title, name, checkable=True)
        layout = QFormLayout(self)
        layout.addRow("Min:", self.spin_min)
        layout.addRow("Max:", self.spin_max)
        layout.addRow("Unit:", self.combo_unit)


class OptionsWidget(BaseGroupBox):
    """Handles logic for miscellaneous options."""

    def __init__(self, title: str, name: str, transfermodes: Sequence[str]) -> None:
        """Initialize the options widget."""
        self.combo_transfermode = QComboBox()
        self.combo_transfermode.addItems(transfermodes)
        self.chk_follow_symlink = QCheckBox()
        self.lineedit_rng_seed = QLineEdit(placeholderText="RNG Seed (optional)", clearButtonEnabled=True)
        self.spin_max_per_dir = QSpinBox(minimum=0, maximum=MAXIMUM_INT)
        self.spin_max_per_dir.setSpecialValueText("Unlimited")
        self._specs = SetupSpecs(
            tips=(
                (self.combo_transfermode, "Select transfer mode"),
                (self.chk_follow_symlink, "If checked, symbolic links followed during file traversal"),
                (self.lineedit_rng_seed, "Seed for random number generator, system clock used if empty"),
                (self.spin_max_per_dir, "Maximum number of files allowed per input folder, 0 for unlimited"),
            ),
            getters=(
                (self.combo_transfermode.currentText, "transfer_mode"),
                (self.chk_follow_symlink.isChecked, "should_follow_symlink"),
                (self.lineedit_rng_seed.text, "rng_seed"),
                (self.spin_max_per_dir.value, "max_per_dir"),
            ),
            setters=(
                (self.combo_transfermode.setCurrentText, "transfer_mode", TransferMode.DRY_RUN),
                (self.chk_follow_symlink.setChecked, "should_follow_symlink", False),
                (self.lineedit_rng_seed.setText, "rng_seed", ""),
                (self.spin_max_per_dir.setValue, "max_per_dir", 0),
            ),
        )
        super().__init__(title, name)
        layout = QFormLayout(self)
        layout.addRow("Transfer mode:", self.combo_transfermode)
        layout.addRow("Follow symbolic links:", self.chk_follow_symlink)
        layout.addRow("RNG Seed:", self.lineedit_rng_seed)
        layout.addRow("Max from one directory:", self.spin_max_per_dir)


class MainConfigLayout(QGridLayout):
    """Layout for MainConfigWidget. Owns the grid, not the widgets."""

    _POSITIONS: ClassVar[dict[str, tuple[int, int, int, int]]] = {
        "root": (0, 0, 1, 3),
        "dest": (1, 0, 1, 3),
        "filecount": (2, 0, 1, 1),
        "directory": (2, 1, 1, 1),
        "filename": (2, 2, 1, 1),
        "dirname": (3, 0, 1, 1),
        "keyword": (3, 1, 1, 1),
        "extension": (3, 2, 1, 1),
        "filesize": (4, 0, 1, 1),
        "duration": (4, 1, 1, 1),
        "options": (4, 2, 1, 1),
    }

    def populate(self, widgets: dict[str, BaseGroupBox]) -> None:
        for name, (row, col, rowspan, colspan) in self._POSITIONS.items():
            self.addWidget(widgets[name], row, col, rowspan, colspan)


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
            "filesize": RangeFilterWidget("File size", "filesize", tuple(SIZE_MAP.keys())),
            "duration": RangeFilterWidget("Duration", "duration", tuple(TIME_MAP.keys())),
            "options": OptionsWidget("Options", "options", available_transfer_fns()),
        }
        layout = MainConfigLayout(self)
        layout.populate(self._widgets)

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

    def __init__(self, w: QWidget, title: str, name: str) -> None:
        """Initialize the base dock widget."""
        super().__init__(title)
        self.setObjectName(name)
        self.setWidget(w)
        f = QDockWidget.DockWidgetFeature
        self.setFeatures(f.DockWidgetMovable | f.DockWidgetFloatable)


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
        self.progbar_files.setMaximum(MAXIMUM_INT)
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
