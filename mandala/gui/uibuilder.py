"""Main module for Mandala."""

from dataclasses import dataclass, field

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from ..config.schemas import MandalaConfigModel
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
        layout = QVBoxLayout()
        layout.addWidget(self.root)
        layout.addWidget(self.dest)

        output_l = QHBoxLayout()
        output_l.addWidget(self.folders)
        output_l.addWidget(self.filecount)
        output_l.addWidget(self.filename)
        output_l.addWidget(self.transfermode)

        layout.addLayout(output_l)
        layout.addWidget(self.keywords)
        layout.addWidget(self.extensions)

        filter_l = QHBoxLayout()
        filter_l.addWidget(self.filesize)
        filter_l.addWidget(self.duration)
        filter_l.addWidget(self.diversity)
        filter_l.addWidget(self.walker)

        layout.addLayout(filter_l)
        layout.addWidget(self.progress)
        layout.addWidget(self.logging)
        return layout

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
