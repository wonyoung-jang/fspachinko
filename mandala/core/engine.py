"""Mandala Engine Module."""

import contextlib
import logging
import shutil
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from .state import EngineStateContext, FolderStats, MandalaEngineStateContext

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ..config import Filecount, Filename, Folder, SizeLimit
    from ..utils import DateTimeProvider, MandalaObserver
    from .quota import DiversityQuota
    from .reporter import ReportWriter
    from .validator import FileValidator
    from .walker import FSWalker


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MandalaEngine:
    """Core engine class for Mandala."""

    root: Path
    dry_run: bool
    validator: FileValidator
    reporter: ReportWriter
    quota: DiversityQuota
    walker: FSWalker
    timestamp: DateTimeProvider
    filecount: Filecount
    filename: Filename
    folder: Folder
    transfer: Callable
    folder_size_limit: SizeLimit
    total_size_limit: SizeLimit

    folderstats: FolderStats = field(default_factory=FolderStats)
    stop_requested: bool = False

    _obs: MandalaObserver = field(init=False)
    _ctx: EngineStateContext = field(init=False)

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        self._ctx = MandalaEngineStateContext(
            stop_requested=self.stop_requested,
            folder=self.folder,
            folderstats=self.folderstats,
            quota=self.quota,
            folder_size_limit=self.folder_size_limit,
            total_size_limit=self.total_size_limit,
        )

    def set_observer(self, observer: MandalaObserver) -> None:
        """Set the observer for the engine."""
        self._obs = observer

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self._ctx.stop_requested = True

    def start(self) -> None:
        """Run the main file copying process."""
        folder_count = self.folder.count
        self._obs.on_progress_total(folder_count)

        for _ in range(folder_count):
            self.process_folder(
                target=self.filecount.get_count(),
                dest=self.folder.create_dest_folder(),
            )

        self._obs.on_finished()

    def process_folder(self, target: int, dest: Path) -> None:
        """Run processing for a single folder."""
        self._prepare_folder(target, dest)
        self._transfer_folder(target, dest)
        self._finalize_folder(target, dest)

    def _prepare_folder(self, target: int, dest: Path) -> None:
        """Prepare state for processing a new folder."""
        self._obs.on_progress(target)
        self.timestamp.refresh()
        self.reporter.reset_for_dest(dest)
        self._ctx.prepare()

    def _transfer_folder(self, target: int, dest: Path) -> None:
        """Process a single folder for file copying."""
        if self._ctx.should_stop(target):
            self.report(msg=self._ctx.state.message)
            return

        for entry in self.walker.walk():
            if self._ctx.should_stop(target):
                self.report(msg=self._ctx.state.message)
                return

            path, size = entry.path, entry.size
            if not self.validator.is_valid(path, size):
                continue

            if not self._transfer_file(path, dest):
                continue

            self._ctx.update_on_success(path, size)
            self._obs.on_count(self.folderstats.count)
            self._obs.on_time()

    def _transfer_file(self, chosen: Path, dest: Path) -> bool:
        """Attempt to copy a file and return success status."""
        count = self.folderstats.count
        chosen_rel = chosen.relative_to(self.root)

        new_target_file = self.filename.calc_dest_target(chosen_rel, dest, count)
        if new_target_file is None:
            return False

        new_target_file_rel = new_target_file.relative_to(dest)
        copy_path_str = f"{chosen_rel} -> {new_target_file_rel}"

        if self.dry_run:
            self.report(msg=f"DRY: {count + 1}: {copy_path_str}")
            return True

        try:
            self.transfer(chosen, new_target_file)
        except (PermissionError, OSError):
            self.report(msg=f"FAILED: {copy_path_str}")
            logger.exception("Failed to copy file: %s", copy_path_str)
            return False
        else:
            self.report(msg=f"{count + 1}: {copy_path_str}")
            return True

    def report(self, msg: str) -> None:
        """Report and log a message."""
        self._obs.on_log(msg)
        self.reporter.record_message(msg)

    def _finalize_folder(self, target: int, dest: Path) -> None:
        """Create and write log at the end of folder."""
        self._obs.on_count_total()

        none_found = self._ctx.is_none_found()
        status_prefix = self._ctx.state.status_prefix

        report = self.reporter.generate_report(
            status=f"{status_prefix}: {self.folderstats.count}/{target} files copied",
            runtime=round(perf_counter() - self.folderstats.starttime, 2),
            size=self.folderstats.curr_size,
        )
        self.report(report)
        self.reporter.save()
        if none_found:
            self._remove_folder_if_empty(dest)

    def _remove_folder_if_empty(self, dest: Path) -> None:
        """Remove the destination folder if it is empty."""
        with contextlib.suppress(OSError):
            shutil.rmtree(dest)
