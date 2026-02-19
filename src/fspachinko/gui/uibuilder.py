"""Main module."""

from dataclasses import dataclass, field

from PySide6.QtWidgets import QVBoxLayout

from ..core import ConfigModel
from .components import (
    DestPathSelectorWidget,
    DirectoryCreateWidget,
    DirnameFilterWidget,
    DurationFilterWidget,
    ExtensionFilterWidget,
    FileCountWidget,
    FilenamerWidget,
    KeywordFilterWidget,
    LogWidget,
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
    dircreator: DirectoryCreateWidget = field(default_factory=DirectoryCreateWidget)
    filenamer: FilenamerWidget = field(default_factory=FilenamerWidget)
    dirname_filter: DirnameFilterWidget = field(default_factory=DirnameFilterWidget)
    keyword_filter: KeywordFilterWidget = field(default_factory=KeywordFilterWidget)
    extension_filter: ExtensionFilterWidget = field(default_factory=ExtensionFilterWidget)
    filesize_filter: SizeFilterWidget = field(default_factory=SizeFilterWidget)
    duration_filter: DurationFilterWidget = field(default_factory=DurationFilterWidget)
    options: OptionsWidget = field(default_factory=OptionsWidget)
    progress: ProgressWidget = field(default_factory=ProgressWidget)
    logging: LogWidget = field(default_factory=LogWidget)

    def build(self) -> QVBoxLayout:
        """Set up the main UI layouts."""
        layout = QVBoxLayout()
        layout.addWidget(self.root)
        layout.addWidget(self.dest)
        layout.addWidget(self.filecount)
        layout.addWidget(self.dircreator)
        layout.addWidget(self.filenamer)
        layout.addWidget(self.dirname_filter)
        layout.addWidget(self.keyword_filter)
        layout.addWidget(self.extension_filter)
        layout.addWidget(self.filesize_filter)
        layout.addWidget(self.duration_filter)
        layout.addWidget(self.options)
        layout.addWidget(self.logging)
        layout.addWidget(self.progress)
        return layout

    def get_config(self) -> ConfigModel:
        """Get the current configuration from all widgets."""
        return ConfigModel(
            root=self.root.get_config(),
            dest=self.dest.get_config(),
            filecount=self.filecount.get_config(),
            folder=self.dircreator.get_config(),
            filename=self.filenamer.get_config(),
            directory_name=self.dirname_filter.get_config(),
            keyword=self.keyword_filter.get_config(),
            extension=self.extension_filter.get_config(),
            filesize=self.filesize_filter.get_config(),
            duration=self.duration_filter.get_config(),
            options=self.options.get_config(),
        )
