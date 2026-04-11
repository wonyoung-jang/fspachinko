"""Handlers module."""

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from itertools import islice
from typing import TYPE_CHECKING

from fspachinko.domain.events import (
    DirectoryStarted,
    DirectoryTransferred,
    FileTransferred,
    PipelineConfigured,
    RunFinished,
    RunStarted,
)
from fspachinko.domain.model import DestinationDirectory, DiversityQuota, FSEntry, TransferJob

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from fspachinko.adapters.filesystem import AbstractFilesystem
    from fspachinko.adapters.loggers import AbstractLogger
    from fspachinko.adapters.pipeline import AbstractPipeline
    from fspachinko.config import ConfigModelBootstrapper
    from fspachinko.domain.commands import ConfigurePipeline, RunTransferJob, SaveConfiguration, StopProcess
    from fspachinko.domain.events import Event
    from fspachinko.helpers import ReportWriter


##################################################################################
######## COMMAND HANDLERS ########################################################
##################################################################################


@dataclass(slots=True)
class ConfigurePipelineHandler:
    """Handle the ConfigurePipeline command."""

    configurator: ConfigModelBootstrapper

    def __call__(self, cmd: ConfigurePipeline) -> Iterator[Event]:
        """Handle the ConfigurePipeline command."""
        c = cmd.config
        self.configurator.apply(c)
        yield PipelineConfigured(dir_count=c.directory.count)


def _filter_parallel(walk: Iterator[FSEntry], fn: Callable[[FSEntry], bool]) -> Iterator[FSEntry]:
    """Filter files in parallel using a ThreadPoolExecutor."""
    with ThreadPoolExecutor() as executor:
        while chunk := tuple(islice(walk, 5)):
            results = executor.map(fn, chunk)
            for entry, is_valid in zip(chunk, results, strict=True):
                if is_valid:
                    yield entry


@dataclass(slots=True)
class RunTransferJobHandler:
    """Handle the RunTransferJob command."""

    job: TransferJob
    filesystem: AbstractFilesystem
    pipeline: AbstractPipeline

    def __call__(self, cmd: RunTransferJob) -> Iterator[Event]:
        """Handle the RunTransferJob command.

        Side-effects/Outputs:
        - Destination directory may be created.
        - Destination logs may be created.
        - Files may be transferred.
        """
        yield RunStarted()
        self.job.is_stop_requested = False
        self.job.quota = DiversityQuota(cmd.root, cmd.max_per_dir, cmd.unique_files_only)
        for dst in self._iterate_inputs():
            if self.job.is_stop_condition:
                break
            self.job.start_directory()
            yield DirectoryStarted(path=dst.path, target_qty=dst.target_qty)
            yield from self._transfer_dir(dst)
            yield DirectoryTransferred(
                path=dst.path,
                size=dst.size,
                count=dst.count,
                target_qty=dst.target_qty,
                is_success=dst.is_success,
                is_empty_creation=dst.is_empty_creation,
                is_stop_requested=self.job.is_stop_requested,
                is_root_locked=self.job.is_root_locked,
            )
        yield RunFinished()

    def _iterate_inputs(self) -> Iterator[DestinationDirectory]:
        """Iterate over the input destination directories."""
        while self.pipeline.inputs:
            dest_dir, target_qty, should_create = self.pipeline.inputs.popleft()
            dst = DestinationDirectory(path=dest_dir, target_qty=target_qty, should_create=should_create)
            if should_create:
                self.filesystem.make_directory(dest_dir)
            else:
                # Working with an existing dir, need to populate file tracking
                # to not overwrite existing files and keep track of stats
                for path, size in self.filesystem.get_existing_files_for_existing_dest(dest_dir):
                    dst.add(path, size)
            yield dst

    def _transfer_dir(self, dst: DestinationDirectory) -> Iterator[Event]:
        """Transfer files to a destination directory."""
        walk = self.pipeline.walk()
        filtered = _filter_parallel(walk, self.pipeline.filter_file)
        with ThreadPoolExecutor() as executor:
            futures: dict[Future[None], tuple[FSEntry, str]] = {}
            for entry in filtered:
                if dst.is_success or self.job.is_stop_condition:
                    break
                if not self.job.can_accept(entry):
                    continue
                if (newpath := self.pipeline.get_new_path(dst, entry)) is None:
                    continue
                self.job.register_transfer(dst, entry, newpath)
                future = executor.submit(self.pipeline.transfer_file, entry.path, newpath)
                futures[future] = (entry, newpath)
                done = [f for f in futures if f.done()]
                for f in done:
                    _entry, _newpath = futures.pop(f)
                    f.result()
                    yield FileTransferred(src=_entry.path, dst=_newpath)
            for f in as_completed(futures):
                entry, newpath = futures.pop(f)
                f.result()
                yield FileTransferred(src=entry.path, dst=newpath)


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

    filesystem: AbstractFilesystem

    def __call__(self, cmd: SaveConfiguration) -> None:
        """Handle the SaveConfiguration command."""
        self.filesystem.save_json(cmd.path, cmd.config)


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

    filesystem: AbstractFilesystem
    logger: AbstractLogger
    reporter: type[ReportWriter]

    def __call__(self, evt: DirectoryTransferred) -> None:
        """Handle the DirectoryTransferred event."""
        path = evt.path
        is_empty_creation = evt.is_empty_creation
        report = self.reporter(
            path=path,
            size=evt.size,
            count=evt.count,
            target_qty=evt.target_qty,
            is_success=evt.is_success,
            is_empty_creation=is_empty_creation,
            is_stop_requested=evt.is_stop_requested,
            is_root_locked=evt.is_root_locked,
        )
        self.logger.info("%s", report)
        self.logger.remove_dest_log_filehandler(path)
        if is_empty_creation:
            self.filesystem.remove_directory(path)


@dataclass(slots=True)
class RunFinishedHandler:
    """Handle the RunFinished event."""

    logger: AbstractLogger

    def __call__(self, _evt: RunFinished) -> None:
        """Handle the RunFinished event."""
        self.logger.info("Transfer job finished.")
