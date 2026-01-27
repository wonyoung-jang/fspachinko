"""Mandala Engine Module."""

import contextlib
import logging
import shutil
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ..config import Filecount, Filename
    from ..utils import MandalaObserver
    from .reporter import ReportWriter
    from .state import EngineStateContext
    from .validator import FileValidator
    from .walker import FSWalker


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MandalaEngine:
    """Core engine class for Mandala."""

    root: Path
    validator: FileValidator
    reporter: ReportWriter
    walker: FSWalker
    filecount: Filecount
    filename: Filename
    transfer_fn: Callable
    _ctx: EngineStateContext
    _obs: MandalaObserver = field(init=False)

    def set_observer(self, observer: MandalaObserver) -> None:
        """Set the observer for the engine."""
        self._obs = observer

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self._ctx.stop_requested = True

    def start(self) -> None:
        """Run the main file copying process."""
        folder_count = self._ctx.folder.count
        self._obs.on_progress_total(folder_count)

        for _ in range(folder_count):
            self.process_folder(
                target=self.filecount.get_count(),
                dest=self._ctx.folder.create_dest_folder(),
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
        self.reporter.reset_for_dest(dest)
        self._ctx.prepare()

    def _transfer_folder(self, target: int, dest: Path) -> None:
        """Process a single folder for file copying."""
        if self._ctx.should_stop(target):
            self.report_state()
            return

        for entry in self.walker.walk():
            if self._ctx.should_stop(target):
                self.report_state()
                return

            path, size = entry.path, entry.size
            if not self.validator.is_valid(path, size):
                continue

            if not self._transfer_file(path, dest):
                continue

            self._ctx.update_on_success(path, size)
            self._obs.on_count(self._ctx.folderstats.count)
            self._obs.on_time()

    def _transfer_file(self, chosen: Path, dest: Path) -> bool:
        """Attempt to copy a file and return success status."""
        count = self._ctx.folderstats.count
        chosen_rel = chosen.relative_to(self.root)

        new_target_file = self.filename.calc_dest_target(chosen_rel, dest, count)
        if new_target_file is None:
            return False

        new_target_file_rel = new_target_file.relative_to(dest)
        copy_path_str = f"{count + 1}: {chosen_rel} -> {new_target_file_rel}"

        if self._ctx.is_dry_run(copy_path_str):
            self.report_state()
            return True

        try:
            self.transfer_fn(chosen, new_target_file)
        except (PermissionError, OSError):
            self._ctx.set_errored(copy_path_str)
            self.report_state()
            return False

        self._ctx.set_transferred(copy_path_str)
        self.report_state()
        return True

    def report_state(self) -> None:
        """Report the current engine state."""
        self.report(msg=self._ctx.state.message)

    def report(self, msg: str) -> None:
        """Report and log a message."""
        self._obs.on_log(msg)
        self.reporter.record_message(msg)

    def _finalize_folder(self, target: int, dest: Path) -> None:
        """Create and write log at the end of folder."""
        self._obs.on_count_total()

        none_found = self._ctx.is_none_found()
        status_prefix = self._ctx.state.prefix

        report = self.reporter.generate_report(
            status=f"{status_prefix}: {self._ctx.folderstats.count}/{target} files copied",
            runtime=round(perf_counter() - self._ctx.folderstats.starttime, 2),
            size=self._ctx.folderstats.curr_size,
        )
        self.report(report)
        self.reporter.save()
        if none_found:
            self._remove_folder_if_empty(dest)

    def _remove_folder_if_empty(self, dest: Path) -> None:
        """Remove the destination folder if it is empty."""
        with contextlib.suppress(OSError):
            shutil.rmtree(dest)
