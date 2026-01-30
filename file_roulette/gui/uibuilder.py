"""Main module for File Roulette."""

from dataclasses import dataclass, field

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QTabWidget, QVBoxLayout, QWidget

from ..config import FileRouletteConfigModel
from .components import (
    DestPathSelectorWidget,
    DurationFilterWidget,
    ExtensionsFilterWidget,
    FileCountWidget,
    FilenameWidget,
    FolderCreatorWidget,
    FolderSizeLimitWidget,
    KeywordsFilterWidget,
    ListIncludeExcludeFilterWidget,
    LoggingWidget,
    MinMaxFilterWidget,
    OptionsWidget,
    PathSelectorWidget,
    ProgressWidget,
    RootPathSelectorWidget,
    SizeFilterWidget,
    SizeLimitWidget,
    TotalSizeLimitWidget,
    TransferModeWidget,
)


@dataclass(slots=True)
class UIBuilder:
    """Main Widget Builder for File Roulette."""

    root: PathSelectorWidget = field(default_factory=RootPathSelectorWidget)
    dest: PathSelectorWidget = field(default_factory=DestPathSelectorWidget)
    filecount: FileCountWidget = field(default_factory=FileCountWidget)
    folders: FolderCreatorWidget = field(default_factory=FolderCreatorWidget)
    filename: FilenameWidget = field(default_factory=FilenameWidget)
    transfermode: TransferModeWidget = field(default_factory=TransferModeWidget)
    keywords: ListIncludeExcludeFilterWidget = field(default_factory=KeywordsFilterWidget)
    extensions: ListIncludeExcludeFilterWidget = field(default_factory=ExtensionsFilterWidget)
    filesize: MinMaxFilterWidget = field(default_factory=SizeFilterWidget)
    duration: MinMaxFilterWidget = field(default_factory=DurationFilterWidget)
    folder_size_limit: SizeLimitWidget = field(default_factory=FolderSizeLimitWidget)
    total_size_limit: SizeLimitWidget = field(default_factory=TotalSizeLimitWidget)
    options: OptionsWidget = field(default_factory=OptionsWidget)
    progress: ProgressWidget = field(default_factory=ProgressWidget)
    logging: LoggingWidget = field(default_factory=LoggingWidget)

    def build_layout(self) -> QVBoxLayout:
        """Set up the main UI layouts."""
        # 1. Path Selection Section (Top)
        paths = QWidget()
        path_layout = QVBoxLayout(paths)
        path_layout.addWidget(self.root)
        path_layout.addWidget(self.dest)

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

        # Row 2: Size Limits
        filter_layout.addWidget(self.folder_size_limit, 2, 0)
        filter_layout.addWidget(self.total_size_limit, 2, 1)

        tabs.addTab(tab_filters, "Filters && Rules")

        # --- Tab 3: Options ---
        options_widget = QWidget()
        options_layout = QHBoxLayout(options_widget)
        options_layout.addWidget(self.options)

        tabs.addTab(options_widget, "Options")

        # 3. Assemble Main Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(paths)
        main_layout.addWidget(tabs)
        main_layout.addWidget(self.logging)
        main_layout.addWidget(self.progress)
        return main_layout

    def get_config(self) -> FileRouletteConfigModel:
        """Get the current configuration from all widgets."""
        return FileRouletteConfigModel(
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
            folder_size_limit=self.folder_size_limit.get_config(),
            total_size_limit=self.total_size_limit.get_config(),
            options=self.options.get_config(),
        )
