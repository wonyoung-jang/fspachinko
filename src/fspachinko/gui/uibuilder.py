"""Main module."""

from dataclasses import dataclass, field

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..core import ConfigModel
from .components import (
    DestPathSelectorWidget,
    DirectoryFilterWidget,
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
)


@dataclass(slots=True)
class UIBuilder:
    """Main Widget Builder."""

    root: PathSelectorWidget = field(default_factory=RootPathSelectorWidget)
    dest: PathSelectorWidget = field(default_factory=DestPathSelectorWidget)
    filecount: FileCountWidget = field(default_factory=FileCountWidget)
    folders: FolderCreatorWidget = field(default_factory=FolderCreatorWidget)
    filename: FilenameWidget = field(default_factory=FilenameWidget)
    directory_name_filter: ListIncludeExcludeFilterWidget = field(default_factory=DirectoryFilterWidget)
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

        # Left widget
        output_widget = QWidget()
        output_layout = QHBoxLayout(output_widget)
        output_layout.addWidget(self.filecount)
        output_layout.addWidget(self.folders)

        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)
        filter_layout.addWidget(self.directory_name_filter)
        filter_layout.addWidget(self.keywords)
        filter_layout.addWidget(self.extensions)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(output_widget)
        left_layout.addWidget(self.filename)
        left_layout.addWidget(filter_widget)

        # Right widget
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

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(size_widget)
        right_layout.addWidget(size_limit_widget)
        right_layout.addWidget(options_widget)

        # Body widget
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.addWidget(left_widget)
        body_layout.addWidget(right_widget)

        # Assemble Main Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(path_widget)
        main_layout.addWidget(body_widget)
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
            directory_name=self.directory_name_filter.get_config(),
            keyword=self.keywords.get_config(),
            extension=self.extensions.get_config(),
            filesize=self.filesize.get_config(),
            duration=self.duration.get_config(),
            folder_size_limit=self.folder_size_limit.get_config(),
            total_size_limit=self.total_size_limit.get_config(),
            options=self.options.get_config(),
        )
