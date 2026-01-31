"""Main module for File Roulette."""

from dataclasses import dataclass, field

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..config import ConfigModel
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
        path_widget = QWidget()
        path_layout = QVBoxLayout(path_widget)
        path_layout.addWidget(self.root)
        path_layout.addWidget(self.dest)

        output_widget = QWidget()
        output_layout = QHBoxLayout(output_widget)
        output_layout.addWidget(self.filecount)
        output_layout.addWidget(self.transfermode)
        output_layout.addWidget(self.folders)
        output_layout.addWidget(self.filename)

        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)
        filter_layout.addWidget(self.keywords)
        filter_layout.addWidget(self.extensions)

        size_widget = QWidget()
        size_layout = QHBoxLayout(size_widget)
        size_layout.addWidget(self.filesize)
        size_layout.addWidget(self.duration)

        size_limit_widget = QWidget()
        size_limit_layout = QHBoxLayout(size_limit_widget)
        size_limit_layout.addWidget(self.folder_size_limit)
        size_limit_layout.addWidget(self.total_size_limit)

        options_widget = QWidget()
        options_layout = QHBoxLayout(options_widget)
        options_layout.addWidget(self.options)

        # Assemble Main Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(path_widget)
        main_layout.addWidget(output_widget)
        main_layout.addWidget(filter_widget)
        main_layout.addWidget(size_widget)
        main_layout.addWidget(size_limit_widget)
        main_layout.addWidget(options_widget)
        main_layout.addWidget(self.logging)
        main_layout.addWidget(self.progress)
        return main_layout

    def get_config(self) -> ConfigModel:
        """Get the current configuration from all widgets."""
        return ConfigModel(
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
