"""GUI components in PySide6."""

from dataclasses import dataclass
from os.path import exists, isdir
from typing import TYPE_CHECKING, Any, ClassVar

from PySide6.QtCore import Qt, QUrl, Slot
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
    from collections.abc import Sequence

    from PySide6.QtGui import QDragEnterEvent, QDropEvent


SELF = ""  # Sentinel value for referring to the widget itself in FieldSpec


@dataclass(slots=True)
class GetterSpec:
    """Specification for config keys."""

    key: str = ""
    fn: str = ""


@dataclass(slots=True)
class SetterSpec:
    """Specification for config keys."""

    key: str = ""
    fn: str = ""
    fallback: object = None


@dataclass(slots=True)
class SignalSpec:
    """Specification for signals/slots."""

    signal: str = ""
    slot_attr: str = ""
    slot: str = ""


@dataclass(slots=True)
class FieldSpec:
    """Specification for subwidgets."""

    name: str = ""
    getter: GetterSpec | None = None
    setters: list[SetterSpec] | None = None
    signals: list[SignalSpec] | None = None
    tip: str = ""


@dataclass(slots=True)
class LayoutSpec:
    """Specification for widget layouts."""

    layout: type
    adder: str
    args: Sequence[Any]


class BaseGroupBox(QGroupBox):
    """Base class for group boxes with common functionality."""

    FIELDS: ClassVar[Sequence[FieldSpec]] = ()

    def __init__(self, title: str, name: str, *, checkable: bool = False) -> None:
        """Initialize the base group box."""
        super().__init__()
        self.setTitle(title)
        self.setObjectName(name)
        self.setCheckable(checkable)
        self.setFlat(True)
        self._wire_slots()
        self._set_tips()
        self._set_layout()

    @property
    def config(self) -> dict:
        """Return clean data for the config."""
        config = {}
        for field in self.FIELDS:
            _name, _getter = field.name, field.getter
            if _getter is None:
                continue
            obj = getattr(self, _name) if _name else self
            getter = getattr(obj, _getter.fn)
            config[_getter.key] = getter()
        return {self.objectName(): config}

    def restore(self, config: dict) -> None:
        """Restore the widget from config data."""
        section = config.get(self.objectName(), {})
        for field in self.FIELDS:
            _name, _setters = field.name, field.setters
            if _setters is None:
                continue
            obj = getattr(self, _name) if _name else self
            for _setter in _setters:
                setter = getattr(obj, _setter.fn)
                value = section.get(_setter.key, _setter.fallback)
                setter(value)

    def _wire_slots(self) -> None:
        """Wire up any custom signals/slots."""
        for field in self.FIELDS:
            _name, _signals = field.name, field.signals
            if _signals is None:
                continue
            widget = getattr(self, _name) if _name else self
            for _signal in _signals:
                signal = getattr(widget, _signal.signal)
                slot_attr = getattr(self, _signal.slot_attr) if _signal.slot_attr else self
                slot = getattr(slot_attr, _signal.slot)
                signal.connect(slot)

    def _set_tips(self) -> None:
        """Set tooltips for all widgets based on TIPS_SPEC."""
        for field in self.FIELDS:
            if widget := getattr(self, field.name, None):
                set_qt_tips(widget, field.tip)

    def _set_layout(self) -> None:
        """Set the layout for the group box."""
        _layout = getattr(self, "_layout", None)
        if _layout is None or not isinstance(_layout, LayoutSpec):
            return
        layout_cls = _layout.layout
        layout = layout_cls(self)
        adder = getattr(layout, _layout.adder)
        for args in _layout.args:
            if isinstance(args, tuple):
                widget, *params = args
                adder(widget, *params)
            else:
                adder(args)


class PathSelectorWidget(BaseGroupBox):
    """Handles logic for selecting a path."""

    FIELDS: ClassVar[Sequence[FieldSpec]] = (
        FieldSpec(
            name="lbl_selected",
            getter=GetterSpec(key="path", fn="text"),
            setters=[SetterSpec(key="path", fn="setText", fallback="")],
            tip="Currently selected folder",
        ),
        FieldSpec(
            name="btn_browse",
            signals=[SignalSpec(signal="clicked", slot_attr="", slot="browse")],
            tip="Browse",
        ),
        FieldSpec(
            name="btn_open",
            signals=[SignalSpec(signal="clicked", slot_attr="", slot="open")],
            tip="Open in file explorer",
        ),
    )

    def __init__(self, title: str, name: str) -> None:
        """Initialize the path selector widget."""
        self.lbl_selected = QLabel()
        self.btn_browse = QPushButton(get_qt_icon("browse"), "")
        self.btn_open = QPushButton(get_qt_icon("open_dir"), "")
        super().__init__(title, name)
        layout = QHBoxLayout(self)
        layout.addWidget(self.lbl_selected, 1)
        layout.addWidget(self.btn_browse)
        layout.addWidget(self.btn_open)
        self.setLayout(layout)
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

    FIELDS: ClassVar[Sequence[FieldSpec]] = (
        FieldSpec(
            name=SELF,
            setters=[SetterSpec(key="is_rand_enabled", fn="restore_randstate", fallback=False)],
        ),
        FieldSpec(
            name="radio_fixed",
            signals=[SignalSpec(signal="toggled", slot_attr="spin_fixed", slot="setEnabled")],
            tip="Select fixed file count",
        ),
        FieldSpec(
            name="radio_rand",
            getter=GetterSpec(key="is_rand_enabled", fn="isChecked"),
            signals=[
                SignalSpec(signal="toggled", slot_attr="spin_min_rand", slot="setEnabled"),
                SignalSpec(signal="toggled", slot_attr="spin_max_rand", slot="setEnabled"),
            ],
            tip="Select random file count",
        ),
        FieldSpec(
            name="spin_fixed",
            getter=GetterSpec(key="count", fn="value"),
            setters=[SetterSpec(key="count", fn="setValue", fallback=1)],
            tip="Number of files to copy",
        ),
        FieldSpec(
            name="spin_min_rand",
            getter=GetterSpec(key="rand_min", fn="value"),
            setters=[SetterSpec(key="rand_min", fn="setValue", fallback=1)],
            signals=[SignalSpec(signal="valueChanged", slot_attr="spin_max_rand", slot="setMinimum")],
            tip="Minimum random file count",
        ),
        FieldSpec(
            name="spin_max_rand",
            getter=GetterSpec(key="rand_max", fn="value"),
            setters=[SetterSpec(key="rand_max", fn="setValue", fallback=10)],
            signals=[SignalSpec(signal="valueChanged", slot_attr="spin_min_rand", slot="setMaximum")],
            tip="Maximum random file count",
        ),
    )

    def __init__(self, title: str, name: str) -> None:
        """Initialize the file count widget."""
        self.radio_fixed = QRadioButton("Fixed")
        self.spin_fixed = QSpinBox(minimum=1, maximum=MAXIMUM_INT)
        self.radio_rand = QRadioButton("Random")
        self.spin_min_rand = QSpinBox(minimum=1, maximum=MAXIMUM_INT)
        self.spin_max_rand = QSpinBox(minimum=2, maximum=MAXIMUM_INT)
        super().__init__(title, name)
        layout = QGridLayout(self)
        layout.addWidget(self.radio_fixed, 0, 0)
        layout.addWidget(self.radio_rand, 1, 0)
        layout.addWidget(self.spin_fixed, 0, 1)
        layout.addWidget(self.spin_min_rand, 1, 1)
        layout.addWidget(self.spin_max_rand, 2, 1)

    def restore_randstate(self, is_rand_enabled: bool) -> None:  # noqa: FBT001
        """Set the radio buttons based on the is_rand_enabled value."""
        self.radio_rand.setChecked(is_rand_enabled)
        self.radio_fixed.setChecked(not is_rand_enabled)
        self.spin_fixed.setEnabled(not is_rand_enabled)
        self.spin_min_rand.setEnabled(is_rand_enabled)
        self.spin_max_rand.setEnabled(is_rand_enabled)


class DirectoryCreateWidget(BaseGroupBox):
    """Handles logic for creating folders."""

    FIELDS: ClassVar[Sequence[FieldSpec]] = (
        FieldSpec(
            name=SELF,
            getter=GetterSpec(key="is_enabled", fn="isChecked"),
            setters=[SetterSpec(key="is_enabled", fn="setChecked", fallback=False)],
        ),
        FieldSpec(
            name="spinbox_folder_count",
            getter=GetterSpec(key="count", fn="value"),
            setters=[SetterSpec(key="count", fn="setValue", fallback=1)],
            tip="Number of folders to create",
        ),
        FieldSpec(
            name="lineedit_folder_name",
            getter=GetterSpec(key="name", fn="text"),
            setters=[SetterSpec(key="name", fn="setText", fallback="fsp_output")],
            tip="Template for naming created folders",
        ),
    )

    def __init__(self, title: str, name: str) -> None:
        """Initialize the create folders widget."""
        self.spinbox_folder_count = QSpinBox(minimum=1, maximum=MAXIMUM_INT)
        self.lineedit_folder_name = QLineEdit(placeholderText="Ex: Random_Files", clearButtonEnabled=True)
        super().__init__(title, name, checkable=True)
        layout = QFormLayout(self)
        layout.addRow("Count:", self.spinbox_folder_count)
        layout.addRow("Name:", self.lineedit_folder_name)


class FilenamerWidget(BaseGroupBox):
    """Handles logic for filename template settings."""

    FIELDS: ClassVar[Sequence[FieldSpec]] = (
        FieldSpec(
            name=SELF,
            getter=GetterSpec(key="is_enabled", fn="isChecked"),
            setters=[SetterSpec(key="is_enabled", fn="setChecked", fallback=False)],
        ),
        FieldSpec(
            name="lineedit_template",
            getter=GetterSpec(key="template", fn="text"),
            setters=[SetterSpec(key="template", fn="setText", fallback=FilenameTemplate.ORIGINAL)],
            tip="File rename template, use 'Insert tag' button to add tags",
        ),
        FieldSpec(
            name="btn_insert",
            tip="Insert tag into template at cursor position",
        ),
        FieldSpec(
            name="menu",
            tip="Select tag to insert into template",
        ),
    )

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

    FIELDS: ClassVar[Sequence[FieldSpec]] = (
        FieldSpec(
            name=SELF,
            getter=GetterSpec(key="is_enabled", fn="isChecked"),
            setters=[SetterSpec(key="is_enabled", fn="setChecked", fallback=False)],
        ),
        FieldSpec(
            name="lineedit_filter",
            getter=GetterSpec(key="text", fn="text"),
            setters=[SetterSpec(key="text", fn="setText", fallback="")],
            tip="Enter items separated by commas",
        ),
        FieldSpec(
            name="radio_include",
            getter=GetterSpec(key="should_include", fn="isChecked"),
            setters=[SetterSpec(key="should_include", fn="setChecked", fallback=True)],
            tip="Include only items matching filter",
        ),
        FieldSpec(
            name="radio_exclude",
            tip="Exclude any items matching filter",
        ),
    )

    def __init__(self, title: str, name: str) -> None:
        """Initialize the dual list widget."""
        self.lineedit_filter = QLineEdit(placeholderText="comma,separated,items", clearButtonEnabled=True)
        self.radio_include = QRadioButton("Include")
        self.radio_exclude = QRadioButton("Exclude")
        super().__init__(title, name, checkable=True)
        layout = QGridLayout(self)
        layout.addWidget(self.lineedit_filter, 0, 0, 1, 2)
        layout.addWidget(self.radio_include, 1, 0)
        layout.addWidget(self.radio_exclude, 1, 1, Qt.AlignmentFlag.AlignLeft)


class RangeFilterWidget(BaseGroupBox):
    """Handles logic for ranges (min/max), e.g., Size or Duration."""

    FIELDS: ClassVar[Sequence[FieldSpec]] = (
        FieldSpec(
            name=SELF,
            getter=GetterSpec(key="is_enabled", fn="isChecked"),
            setters=[SetterSpec(key="is_enabled", fn="setChecked", fallback=False)],
        ),
        FieldSpec(
            name="spin_min",
            getter=GetterSpec(key="minimum", fn="value"),
            setters=[SetterSpec(key="minimum", fn="setValue", fallback=0.0)],
            signals=[SignalSpec(signal="valueChanged", slot_attr="spin_max", slot="setMinimum")],
            tip="Minimum value",
        ),
        FieldSpec(
            name="spin_max",
            getter=GetterSpec(key="maximum", fn="value"),
            setters=[SetterSpec(key="maximum", fn="setValue", fallback=10.0)],
            signals=[SignalSpec(signal="valueChanged", slot_attr="spin_min", slot="setMaximum")],
            tip="Maximum value",
        ),
        FieldSpec(
            name="combo_unit",
            getter=GetterSpec(key="unit", fn="currentText"),
            setters=[SetterSpec(key="unit", fn="setCurrentText", fallback="")],
            tip="Unit",
        ),
    )

    def __init__(self, title: str, name: str, items: Sequence[str]) -> None:
        """Initialize the range filter widget."""
        self.spin_min = QDoubleSpinBox(minimum=0.0, maximum=float("inf"))
        self.spin_max = QDoubleSpinBox(minimum=0.0, maximum=float("inf"))
        self.combo_unit = QComboBox()
        self.combo_unit.addItems(items)
        super().__init__(title, name, checkable=True)
        layout = QFormLayout(self)
        layout.addRow("Min:", self.spin_min)
        layout.addRow("Max:", self.spin_max)
        layout.addRow("Unit:", self.combo_unit)


class OptionsWidget(BaseGroupBox):
    """Handles logic for miscellaneous options."""

    FIELDS: ClassVar[Sequence[FieldSpec]] = (
        FieldSpec(
            name="combo_transfermode",
            getter=GetterSpec(key="transfer_mode", fn="currentText"),
            setters=[SetterSpec(key="transfer_mode", fn="setCurrentText", fallback=TransferMode.DRY_RUN)],
            tip="Select transfer mode",
        ),
        FieldSpec(
            name="chk_follow_symlink",
            getter=GetterSpec(key="should_follow_symlink", fn="isChecked"),
            setters=[SetterSpec(key="should_follow_symlink", fn="setChecked", fallback=False)],
            tip="If checked, symbolic links followed during file traversal",
        ),
        FieldSpec(
            name="lineedit_rng_seed",
            getter=GetterSpec(key="rng_seed", fn="text"),
            setters=[SetterSpec(key="rng_seed", fn="setText", fallback="")],
            tip="Seed for random number generator, system clock used if empty",
        ),
        FieldSpec(
            name="spin_max_per_dir",
            getter=GetterSpec(key="max_per_dir", fn="value"),
            setters=[SetterSpec(key="max_per_dir", fn="setValue", fallback=0)],
            tip="Maximum number of files allowed per input folder, 0 for unlimited",
        ),
    )

    def __init__(self, title: str, name: str, transfermodes: Sequence[str]) -> None:
        """Initialize the options widget."""
        self.combo_transfermode = QComboBox()
        self.combo_transfermode.addItems(transfermodes)
        self.chk_follow_symlink = QCheckBox()
        self.lineedit_rng_seed = QLineEdit(placeholderText="RNG Seed (optional)", clearButtonEnabled=True)
        self.spin_max_per_dir = QSpinBox(minimum=0, maximum=MAXIMUM_INT)
        self.spin_max_per_dir.setSpecialValueText("Unlimited")
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

    @property
    def file_percentage(self) -> int:
        """Calculate the current file progress percentage."""
        maximum = self.progbar_files.maximum()
        if maximum <= 0:
            return 0
        return int(self.progbar_files.value() * 100 / maximum)
