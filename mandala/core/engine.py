"""Mandala Engine Module."""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ..config import Filecount, Filename
    from ..utils import MandalaObserver
    from .state import EngineContext
    from .validator import FileValidator
    from .walker import FSWalker


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MandalaEngine:
    """Core engine class for Mandala."""

    root: Path
    walker: FSWalker
    validator: FileValidator
    filecount: Filecount
    filename: Filename
    transfer_file: Callable
    _ctx: EngineContext
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
            self.process_folder()

        self._obs.on_finished()

    def process_folder(self) -> None:
        """Run processing for a single folder."""
        target = self.filecount.get_count()
        dest = self._ctx.folder.create_dest_folder()

        self._obs.on_progress(target)
        self._ctx.prepare(dest)

        self._transfer_folder(target, dest)

        self._obs.on_count_total()
        self.report(self._ctx.finalize(target, dest))

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
        chosen_new = self.filename.calc_dest_target(chosen_rel, dest, count)
        if chosen_new is None:
            return False

        msg = f"{count + 1}: {chosen_rel} -> {chosen_new.relative_to(dest)}"

        if self._ctx.is_dry_run(msg):
            self.report_state()
            return True

        try:
            self.transfer_file(chosen, chosen_new)
        except (PermissionError, OSError):
            self._ctx.set_errored(msg)
            self.report_state()
            return False

        self._ctx.set_transferred(msg)
        self.report_state()
        return True

    def report_state(self) -> None:
        """Report the current engine state."""
        self.report(msg=self._ctx.state.message)

    def report(self, msg: str) -> None:
        """Report and log a message."""
        self._obs.on_log(msg)
        self._ctx.reporter.record_message(msg)
