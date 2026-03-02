"""Model classes for the domain."""

from collections import Counter, deque
from dataclasses import dataclass, field
from os.path import join
from time import perf_counter
from typing import TYPE_CHECKING

from ..adapters.filesystemport import remove_directory
from ..core.helpers import convert_byte_to_human_readable_size, get_report, get_status
from .events import DirectoryStarted, FileTransferred, ProcessStarted, ProcessStopped

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ..adapters.filesystemport import AbstractFilesystemPort
    from ..adapters.loggers import AbstractLoggingPort
    from ..adapters.transfer import AbstractTransfer
    from ..adapters.walker import AbstractFSWalker
    from ..core.verbs.dirnamer import AbstractDirectoryNamer
    from ..core.verbs.filecounter import AbstractFileCounter
    from ..core.verbs.filefilter import AbstractFileFilter
    from ..core.verbs.filenamer import AbstractFilenamer
    from .events import Event


@dataclass(slots=True)
class Engine:
    """Core engine class."""

    root: str
    dir_count: int
    is_create_dir: bool

    filecount_fn: AbstractFileCounter
    dirname_fn: AbstractDirectoryNamer
    filefilter_fn: AbstractFileFilter
    filenamer_fn: AbstractFilenamer
    transfer_fn: AbstractTransfer
    walker_fn: AbstractFSWalker

    filesystem: AbstractFilesystemPort
    logging: AbstractLoggingPort

    quota: DiversityQuota

    is_stop_requested: bool = False

    events: deque[Event] = field(default_factory=deque)

    def process(self) -> Iterator[Event]:
        """Run the main file transfer process."""
        yield ProcessStarted(self.dir_count)

        for dir_i in range(1, self.dir_count + 1):
            target_qty = self.filecount_fn()

            yield DirectoryStarted(dir_i, target_qty)
            dst = DestinationDirectory(
                path=self.get_currdir_dest(),  # I/O
                target_qty=target_qty,
                count=0,
                size=0,
                start_time=perf_counter(),
            )
            yield from self.process_dir(dst)
            self.post_process_dir(dst)

        yield ProcessStopped()

    def process_dir(self, dst: DestinationDirectory) -> Iterator[Event]:
        """Process one directory."""
        self.quota.reset()
        self.logging.add_handler(dst.path)
        for e in self.walker_fn():
            if dst.is_success or self.is_stop_requested or self.root in self.quota.locked_dir:
                break

            if not self.can_transfer_file(e) or (newpath := self.get_new_path(e, dst)) is None:
                continue

            if self.transfer_file(e.path, newpath):
                self.quota.update(e)
                dst.count += 1
                dst.size += e.size
                self.logging.info("%s: %s -> %s", dst.count, e.path, newpath)
                yield FileTransferred(dst.count)

    def post_process_dir(self, dst: DestinationDirectory) -> None:
        """Post-process after finishing a directory."""
        status = get_status(
            is_success=dst.is_success,
            is_none_found=dst.is_none_found,
            is_stop_requested=self.is_stop_requested,
            is_create_dir=self.is_create_dir,
            is_root_locked=self.root in self.quota.locked_dir,
        )
        report = get_report(
            dst.path,
            dst.size_str,
            dst.runtime_str,
            dst.count,
            dst.target_qty,
        )

        self.logging.info("%s\n%s", status, report)
        self.logging.remove_handler()

        remove_directory(
            dst.path,
            is_create_dir=self.is_create_dir,
            is_none_found=dst.is_none_found,
        )

    def can_transfer_file(self, e: FSEntry) -> bool:
        """Check if a file can be transferred."""
        return self.quota.can_accept(e) and self.filefilter_fn(e)

    def get_new_path(self, e: FSEntry, dst: DestinationDirectory) -> str | None:
        """Check if the original file name can be used without transfer."""
        ext = e.ext.casefold()
        new_stem = self.filenamer_fn(e, dst.count)
        target = join(dst.path, f"{new_stem}{ext}")
        if self.filesystem.are_files_equal(e.path, target):  # I/O
            return None
        return self.filesystem.get_unique_path(dst.path, new_stem, ext)  # I/O

    def transfer_file(self, src: str, dst: str) -> bool:
        """Transfer a file from src to dst."""
        try:
            self.transfer_fn(src, dst)
        except PermissionError, OSError:
            return False
        return True

    def get_currdir_dest(self) -> str:
        """Get the current directory destination."""
        d = self.dirname_fn()
        return d if not self.is_create_dir else self.filesystem.get_dest_dir_path(d)


@dataclass(slots=True)
class DestinationDirectory:
    """Aggregate: Represents a destination directory for file transfer."""

    path: str
    target_qty: int
    count: int
    size: int
    start_time: float

    @property
    def is_success(self) -> bool:
        """Check if the directory has reached its target quantity."""
        return self.count >= self.target_qty

    @property
    def is_none_found(self) -> bool:
        """Check if no valid files were found."""
        return self.count == 0

    @property
    def size_str(self) -> str:
        """Get the human-readable size string."""
        return convert_byte_to_human_readable_size(self.size)

    @property
    def runtime_str(self) -> str:
        """Get the runtime string."""
        return f"{perf_counter() - self.start_time:.2f}s"


@dataclass(slots=True, frozen=True)
class FSEntry:
    """Value object wrapper for os.DirEntry."""

    path: str
    stem: str
    ext: str
    parent: str
    size: int
    mtime: float
    duration: float = 0.0


@dataclass(slots=True)
class FSPachinkoPin:
    """Represents a 'pin' on the Pachinko board."""

    path: str
    is_scanned: bool = False
    subdirs: list[str] = field(default_factory=list)
    files: list[FSEntry] = field(default_factory=list)


@dataclass(slots=True)
class DiversityQuota:
    """Represents the diversity quota for the process."""

    max_per_dir: int | float
    unique_files_only: bool
    locked_file: set[str] = field(default_factory=set)
    locked_dir: Counter[str] = field(default_factory=Counter)

    def __post_init__(self) -> None:
        """Post-initialization tasks."""
        if self.max_per_dir <= 0:
            self.max_per_dir = float("inf")

    def reset(self) -> None:
        """Reset the locked file and directory sets."""
        self.locked_dir.clear()
        if not self.unique_files_only:
            self.locked_file.clear()

    def can_accept(self, e: FSEntry) -> bool:
        """Check if a file can be accepted based on the diversity quota."""
        if e.path in self.locked_file:
            return False
        return not self.locked_dir[e.parent] >= self.max_per_dir

    def update(self, e: FSEntry) -> None:
        """Update the locked directory count after accepting a file."""
        self.locked_file.add(e.path)
        self.locked_dir[e.parent] += 1
