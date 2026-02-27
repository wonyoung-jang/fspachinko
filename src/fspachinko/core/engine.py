"""Engine Module."""

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from os import makedirs
from os.path import exists, join, relpath
from time import perf_counter
from typing import TYPE_CHECKING

from .constants import DateTimeFormat, StateStatus
from .helpers import (
    are_files_equal,
    calc_unique_path_name_joined,
    convert_byte_to_human_readable_size,
    get_new_fpath,
    remove_directory,
)
from .loggers import get_dest_log_filehandler
from .model import ProcessFinishedEvent

if TYPE_CHECKING:
    from .model import FSEntry
    from .observer import AbstractObserver
    from .verbs.dirnamer import AbstractDirectoryNamer
    from .verbs.filecounter import AbstractFileCounter
    from .verbs.filefilter import AbstractFileFilter
    from .verbs.filenamer import AbstractFilenamer
    from .verbs.transfer import AbstractTransfer
    from .verbs.walker import AbstractFSWalker

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Engine:
    """Core engine class."""

    root: str
    is_create_folder: bool
    dir_count: int
    max_per_dir: int | float
    is_create_unique_dirs: bool

    filecount_fn: AbstractFileCounter
    dirname_fn: AbstractDirectoryNamer
    filefilter_fn: AbstractFileFilter
    filenamer_fn: AbstractFilenamer
    transfer_fn: AbstractTransfer
    walker_fn: AbstractFSWalker
    observer: AbstractObserver

    locked_file: set[str] = field(default_factory=set)
    locked_dir: Counter[str] = field(default_factory=Counter)

    timestamp: str = ""

    is_stop_requested: bool = field(default=False)

    dest: str = ""
    target: int = 0
    file_count: int = 0
    curr_size: int = 0
    start_time: float = 0.0

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        if self.max_per_dir <= 0:
            self.max_per_dir = float("inf")

    @property
    def is_success(self) -> bool:
        """Check if the process finished successfully."""
        return self.file_count == self.target

    @property
    def is_stopped(self) -> bool:
        """Check if the process should be stopped."""
        return self.is_stop_requested or self.is_success or self.is_root_locked

    @property
    def is_none_found(self) -> bool:
        """Check if no valid files were found."""
        return self.file_count == 0 and self.is_create_folder

    @property
    def is_root_locked(self) -> bool:
        """Check if the root directory is locked by the diversity quota."""
        return self.root in self.locked_dir

    def start(self) -> None:
        """Run the main file copying process."""
        self.observer.on_start_process(self.dir_count)

        for idx in range(1, self.dir_count + 1):
            # Perform "resets"
            self.target = self.filecount_fn()
            d = self.dirname_fn()
            dest = calc_unique_path_name_joined(d)
            if not exists(dest):
                makedirs(dest, exist_ok=True)
            self.dest = dest
            self.file_count = 0
            self.curr_size = 0
            self.start_time = perf_counter()
            # Process
            self.process(idx)

        self.observer.on_finished()

    def process(self, idx: int) -> None:
        """Process a single folder for file copying."""
        self.observer.on_directory_start(idx, self.target)

        datetime_now = datetime.now(tz=UTC)
        self.timestamp = datetime_now.strftime(DateTimeFormat.DATETIME)

        self.locked_dir.clear()
        if not self.is_create_unique_dirs:
            self.locked_file.clear()

        log_handler = get_dest_log_filehandler(self.dest)
        logger.addHandler(log_handler)

        _entries = self.walker_fn()
        while not self.is_stopped and (e := next(_entries, None)) is not None:
            self.process_entry(e)

        summary = self.generate_summary()

        logger.info(summary)
        logger.removeHandler(log_handler)
        log_handler.close()

        if self.is_none_found:
            remove_directory(self.dest)

    def process_entry(self, e: FSEntry) -> None:
        """Process a single file entry."""
        if (path := e.path) in self.locked_file:
            return

        self.locked_file.add(path)

        if (parent := e.parent) in self.locked_dir and self.locked_dir[parent] >= self.max_per_dir:
            return

        if not self.filefilter_fn(e):  # I/O if duration
            return

        newstem = self.filenamer_fn(e, self.file_count)
        target = join(self.dest, f"{newstem}{e.ext}")
        if exists(target) and are_files_equal(path, target):  # I/O
            return
        newname = get_new_fpath(self.dest, newstem, e.ext)  # I/O

        try:
            self.transfer_fn(path, newname)  # I/O if not dry run
        except PermissionError, OSError:
            return
        else:
            msg = f"{self.file_count + 1}: {relpath(path, self.root)} -> {relpath(newname, self.dest)}"
            logger.info(msg)

            self.locked_dir[parent] += 1

            self.curr_size += e.size
            self.file_count += 1

            self.observer.on_file_transferred(self.file_count)
            return

    #################
    # Context methods
    #################

    def request_stop(self) -> None:
        """Request to stop the engine."""
        self.is_stop_requested = True

    def get_report_state(self) -> ProcessFinishedEvent:
        """Get the state and message for reporting."""
        status, msg = "UNDEFINED", "UNDEFINED"

        if self.is_success:
            status = StateStatus.SUCCESS
            msg = "Transferred all requested files."
        elif self.is_stop_requested:
            status = StateStatus.USER_STOPPED
            msg = "Stopped by user."
        elif self.is_root_locked:
            status = StateStatus.ALL_FILES_SEARCHED
            msg = "Locked all files by diversity quota."
        elif self.is_none_found:
            if self.is_root_locked:
                status = StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED
                msg = "Found no valid files in root and locked all files by diversity quota."
            else:
                status = StateStatus.NO_FILES_FOUND_FOLDER_DELETED
                msg = "Found no valid files in root."

        return ProcessFinishedEvent(status=status, msg=msg)

    def generate_summary(self) -> str:
        """Generate the summary report."""
        state = self.get_report_state()
        return (
            f"SUMMARY:\n"
            f"{state.msg}\n"
            f"{state.status}: {self.file_count}/{self.target} files transferred\n"
            "------------------------------------------------------------------------\n"
            f"Timestamp:    {self.timestamp}\n"
            f"Root:         {self.root}\n"
            f"Destination:  {self.dest}\n"
            f"Size:         {convert_byte_to_human_readable_size(self.curr_size)}\n"
            f"Runtime:      {perf_counter() - self.start_time:.2f}s\n"
            "========================================================================\n"
        )
