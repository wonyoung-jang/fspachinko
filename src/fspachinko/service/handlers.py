"""Handlers module."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fspachinko.domain.events import (
    DirectoryStarted,
    DirectoryTransferred,
    FileTransferred,
    PipelineConfigured,
    RunFinished,
    RunStarted,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fspachinko.adapters.filesystem import AbstractFilesystem
    from fspachinko.adapters.loggers import AbstractLogger
    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.config import ConfigModelBootstrapper
    from fspachinko.domain.commands import ConfigurePipeline, RunTransferJob, SaveConfiguration, StopProcess
    from fspachinko.domain.events import Event
    from fspachinko.domain.model import DestinationDirectory, TransferJob
    from fspachinko.helpers import ReportWriter


##################################################################################
######## COMMAND HANDLERS ########################################################
##################################################################################


@dataclass(slots=True)
class ConfigurePipelineHandler:
    """Handle the ConfigurePipeline command."""

    pipeline: AbstractPipeline
    configurator: ConfigModelBootstrapper

    def __call__(self, cmd: ConfigurePipeline) -> Iterator[Event]:
        """Handle the ConfigurePipeline command."""
        c = cmd.config
        self.configurator.apply(c, self.pipeline)
        yield PipelineConfigured(dir_count=c.directory.count)


@dataclass(slots=True)
class RunTransferJobHandler:
    """Handle the RunTransferJob command."""

    job: TransferJob
    fs: AbstractFilesystem
    pipeline: AbstractPipeline

    def __call__(self, cmd: RunTransferJob) -> Iterator[Event]:
        """Handle the RunTransferJob command.

        Side-effects/Outputs:
        - Destination directory may be created.
        - Destination logs may be created.
        - Files may be transferred.
        """
        yield RunStarted()
        self.job.root = cmd.root
        self.job.max_per_dir = cmd.max_per_dir
        self.job.is_stop_requested = False

        def _dsts() -> Iterator[DestinationDirectory]:
            """Iterate over the input destination directories."""
            while inputs := self.pipeline.inputs:
                dst = inputs.popleft()
                if dst.should_create:
                    self.fs.make_directory(dst.path)
                else:
                    # Working with an existing dir, need to populate file tracking
                    # to not overwrite existing files and keep track of stats
                    for _path, size in self.fs.get_existing_files_for_existing_dest(dst.path):
                        dst.add(_path, size)
                yield dst

        for dst in _dsts():
            self.job.reset()
            if self.job.is_stop_condition:
                break
            yield DirectoryStarted(path=dst.path, target_qty=dst.target_qty)
            yield from self.pipeline.transfer_dir(self.job, dst)
            yield DirectoryTransferred(
                path=dst.path,
                size=dst.size,
                count=len(dst),
                target_qty=dst.target_qty,
                is_success=dst.is_success,
                is_empty_creation=dst.is_empty_creation,
                is_stop_requested=self.job.is_stop_requested,
                is_root_locked=self.job.is_root_locked,
            )
        yield RunFinished()


@dataclass(slots=True)
class StopProcessHandler:
    """Handle the StopProcess command."""

    job: TransferJob

    def __call__(self, _: StopProcess) -> None:
        """Handle the StopProcess command."""
        self.job.request_stop()


@dataclass(slots=True)
class SaveConfigurationHandler:
    """Handle the SaveConfiguration command."""

    fs: AbstractFilesystem

    def __call__(self, cmd: SaveConfiguration) -> None:
        """Handle the SaveConfiguration command."""
        self.fs.save_json(cmd.path, cmd.config)


################################################################################
######## EVENT HANDLERS ########################################################
################################################################################
@dataclass(slots=True)
class PipelineConfiguredHandler:
    """Handle the PipelineConfigured event."""

    logger: AbstractLogger

    def __call__(self, evt: PipelineConfigured) -> None:
        """Handle the PipelineConfigured event."""
        self.logger.info("Pipeline configured with %s directories to process.", evt.dir_count)


@dataclass(slots=True)
class RunStartedHandler:
    """Handle the RunStarted event."""

    logger: AbstractLogger

    def __call__(self, _evt: RunStarted) -> None:
        """Handle the RunStarted event."""
        self.logger.info("Transfer job started.")


@dataclass(slots=True)
class DirectoryStartedHandler:
    """Handle the DirectoryStarted event."""

    logger: AbstractLogger

    def __call__(self, evt: DirectoryStarted) -> None:
        """Handle the DirectoryStarted event."""
        self.logger.add_dest_log_filehandler(evt.path)
        self.logger.info("Processing directory %s with target quantity: %s", evt.path, evt.target_qty)


@dataclass(slots=True)
class FileTransferredHandler:
    """Handle the FileTransferred event."""

    logger: AbstractLogger

    def __call__(self, evt: FileTransferred) -> None:
        """Handle the FileTransferred event."""
        self.logger.info("'%s' -> '%s'", evt.src, evt.dst)


@dataclass(slots=True)
class DirectoryTransferredHandler:
    """Handle the DirectoryTransferred event."""

    fs: AbstractFilesystem
    logger: AbstractLogger
    reporter: type[ReportWriter]

    def __call__(self, evt: DirectoryTransferred) -> None:
        """Handle the DirectoryTransferred event."""
        self.logger.info("%s", self.reporter(evt))
        self.logger.remove_dest_log_filehandler(evt.path)
        if evt.is_empty_creation:
            self.fs.remove_directory(evt.path)


@dataclass(slots=True)
class RunFinishedHandler:
    """Handle the RunFinished event."""

    logger: AbstractLogger

    def __call__(self, _evt: RunFinished) -> None:
        """Handle the RunFinished event."""
        self.logger.info("Transfer job finished.")
