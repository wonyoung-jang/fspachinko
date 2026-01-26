"""Main module for Mandala."""

from dataclasses import dataclass, field

from PySide6.QtWidgets import QGridLayout, QSizePolicy, QTabWidget, QVBoxLayout, QWidget

from ..config import MandalaConfigModel
from .components import (
    DblRangeFilterWidget,
    DestPathSelectorWidget,
    DiversityFilterWidget,
    DualListFilterWidget,
    DurationFilterWidget,
    ExtensionsFilterWidget,
    FileCountWidget,
    FilenameWidget,
    FolderCreatorWidget,
    KeywordsFilterWidget,
    LoggingWidget,
    PathSelectorWidget,
    ProgressWidget,
    RootPathSelectorWidget,
    SizeFilterWidget,
    TransferModeWidget,
    WalkerWidget,
)


@dataclass(slots=True)
class UIBuilder:
    """Main Widget Builder for Mandala."""

    root: PathSelectorWidget = field(default_factory=RootPathSelectorWidget)
    dest: PathSelectorWidget = field(default_factory=DestPathSelectorWidget)
    filecount: FileCountWidget = field(default_factory=FileCountWidget)
    folders: FolderCreatorWidget = field(default_factory=FolderCreatorWidget)
    filename: FilenameWidget = field(default_factory=FilenameWidget)
    transfermode: TransferModeWidget = field(default_factory=TransferModeWidget)
    keywords: DualListFilterWidget = field(default_factory=KeywordsFilterWidget)
    extensions: DualListFilterWidget = field(default_factory=ExtensionsFilterWidget)
    filesize: DblRangeFilterWidget = field(default_factory=SizeFilterWidget)
    duration: DblRangeFilterWidget = field(default_factory=DurationFilterWidget)
    diversity: DiversityFilterWidget = field(default_factory=DiversityFilterWidget)
    progress: ProgressWidget = field(default_factory=ProgressWidget)
    logging: LoggingWidget = field(default_factory=LoggingWidget)
    walker: WalkerWidget = field(default_factory=WalkerWidget)

    def build_layout(self) -> QVBoxLayout:
        """Set up the main UI layouts."""
        # 1. Path Selection Section (Top)
        path_layout = QVBoxLayout()
        path_layout.addWidget(self.root)
        path_layout.addWidget(self.dest)
        path_layout.setSpacing(5)

        # 2. Main Configuration Tabs
        tabs = QTabWidget()

        # --- Tab 1: Output Settings ---
        tab_output = QWidget()
        output_layout = QGridLayout(tab_output)

        # Column 0: Transfer Configs
        output_layout.addWidget(self.filecount, 0, 0)
        output_layout.addWidget(self.transfermode, 1, 0)

        # Column 1: Organization
        output_layout.addWidget(self.folders, 0, 1)
        output_layout.addWidget(self.filename, 1, 1)

        tab_output.setLayout(output_layout)
        tabs.addTab(tab_output, "Output Settings")

        # --- Tab 2: Filters ---
        tab_filters = QWidget()
        filter_layout = QGridLayout(tab_filters)

        # Row 0: Text based filters
        filter_layout.addWidget(self.keywords, 0, 0)
        filter_layout.addWidget(self.extensions, 0, 1)

        # Row 1: Numeric filters
        filter_layout.addWidget(self.filesize, 1, 0)
        filter_layout.addWidget(self.duration, 1, 1)

        # Row 2: Advanced/Misc
        filter_layout.addWidget(self.diversity, 2, 0)
        filter_layout.addWidget(self.walker, 2, 1)

        tab_filters.setLayout(filter_layout)
        tabs.addTab(tab_filters, "Filters && Rules")

        # 3. Assemble Main Layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(path_layout)
        main_layout.addWidget(tabs)

        # Spacer to prevent logs from eating all space
        self.logging.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        main_layout.addWidget(self.logging, stretch=1)

        main_layout.addWidget(self.progress)

        return main_layout

    def get_config(self) -> MandalaConfigModel:
        """Get the current configuration from all widgets."""
        return MandalaConfigModel(
            root=self.root.get_config(),
            dest=self.dest.get_config(),
            filecount=self.filecount.get_config(),
            folder=self.folders.get_config(),
            filename=self.filename.get_config(),
            transfermode=self.transfermode.get_config(),
            keyword=self.keywords.get_config(),
            extension=self.extensions.get_config(),
            filesize=self.filesize.get_config(),
            duration=self.duration.get_config(),
            diversity=self.diversity.get_config(),
            walker=self.walker.get_config(),
        )
