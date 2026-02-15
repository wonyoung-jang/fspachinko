"""Main module."""

from dataclasses import dataclass, field

from PySide6.QtWidgets import QVBoxLayout

from ..core import ConfigModel
from .components import (
    DestPathSelectorWidget,
    DirectoryFilterWidget,
    DurationFilterWidget,
    ExtensionsFilterWidget,
    FileCountWidget,
    FilenameWidget,
    FolderCreatorWidget,
    KeywordsFilterWidget,
    LoggingWidget,
    OptionsWidget,
    ProgressWidget,
    RootPathSelectorWidget,
    SizeFilterWidget,
)


@dataclass(slots=True)
class UIBuilder:
    """Main Widget Builder."""

    root: RootPathSelectorWidget = field(default_factory=RootPathSelectorWidget)
    dest: DestPathSelectorWidget = field(default_factory=DestPathSelectorWidget)
    filecount: FileCountWidget = field(default_factory=FileCountWidget)
    folders: FolderCreatorWidget = field(default_factory=FolderCreatorWidget)
    filename: FilenameWidget = field(default_factory=FilenameWidget)
    directory_name_filter: DirectoryFilterWidget = field(default_factory=DirectoryFilterWidget)
    keywords: KeywordsFilterWidget = field(default_factory=KeywordsFilterWidget)
    extensions: ExtensionsFilterWidget = field(default_factory=ExtensionsFilterWidget)
    filesize: SizeFilterWidget = field(default_factory=SizeFilterWidget)
    duration: DurationFilterWidget = field(default_factory=DurationFilterWidget)
    options: OptionsWidget = field(default_factory=OptionsWidget)
    progress: ProgressWidget = field(default_factory=ProgressWidget)
    logging: LoggingWidget = field(default_factory=LoggingWidget)

    def build_layout(self) -> QVBoxLayout:
        """Set up the main UI layouts."""
        layout = QVBoxLayout()
        layout.addWidget(self.root)
        layout.addWidget(self.dest)
        layout.addWidget(self.filecount)
        layout.addWidget(self.folders)
        layout.addWidget(self.filename)
        layout.addWidget(self.directory_name_filter)
        layout.addWidget(self.keywords)
        layout.addWidget(self.extensions)
        layout.addWidget(self.filesize)
        layout.addWidget(self.duration)
        layout.addWidget(self.options)
        layout.addWidget(self.logging)
        layout.addWidget(self.progress)
        layout.setSpacing(2)
        return layout

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
            options=self.options.get_config(),
        )
