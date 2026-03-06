"""Model classes for the domain."""

from collections import Counter
from dataclasses import dataclass, field
from os.path import join
from time import perf_counter
from typing import TYPE_CHECKING

from ..helpers import convert_byte_to_human_readable_size, get_report

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ..adapters.filesystemport import AbstractFilesystemPort
    from ..adapters.transfer import AbstractTransfer
    from ..adapters.verbs.dirnamer import AbstractDirectoryNamer
    from ..adapters.verbs.filecounter import AbstractFileCounter
    from ..adapters.verbs.filefilter import AbstractFileFilter
    from ..adapters.verbs.filenamer import AbstractFilenamer
    from ..adapters.walker import AbstractFSWalker


@dataclass(slots=True)
class TransferPipeline:
    """Owns the strategy objects — Engine delegates to this."""

    is_create_dir: bool
    fs: AbstractFilesystemPort
    filefilter_fn: AbstractFileFilter
    filenamer_fn: AbstractFilenamer
    transfer_fn: AbstractTransfer
    walker_fn: AbstractFSWalker
    filecount_fn: AbstractFileCounter
    dirname_fn: AbstractDirectoryNamer

    def walk(self) -> Iterator[FSEntry]:
        """Walk the file system and yield FSEntry objects."""
        return self.walker_fn()

    def get_file_count(self) -> int:
        """Count the number of files to be transferred."""
        return self.filecount_fn()

    def get_dir_name(self) -> str:
        """Get the name for the current directory."""
        return self.dirname_fn()

    def filter_file(self, e: FSEntry) -> bool:
        """Check if a file should be transferred."""
        return self.filefilter_fn(e)

    def get_new_file_stem(self, e: FSEntry, count: int) -> str:
        """Get the new name for a file."""
        return self.filenamer_fn(e, count)

    def transfer_file(self, src: str, dst: str) -> None:
        """Transfer a file from src to dst."""
        self.transfer_fn(src, dst)

    def get_currdir_dest(self) -> str:
        """Get the current directory destination."""
        d = self.get_dir_name()
        match self.is_create_dir:
            case False:
                return d
            case True:
                return self.fs.get_dest_dir_path(d)

    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""
        ext = e.ext.casefold()
        new_stem = self.get_new_file_stem(e, dst.count)
        target = join(dst.path, f"{new_stem}{ext}")
        if self.fs.are_files_equal(e.path, target):
            return None
        return self.fs.get_unique_path(dst.path, new_stem, ext)

    def remove_dst_dir_if_empty(self, path: str, *, none_found: bool) -> None:
        """Remove the destination directory if it is empty."""
        if none_found:
            self.fs.remove_directory(path)


@dataclass(slots=True)
class DestinationDirectory:
    """Aggregate: Represents a destination directory for file transfer."""

    path: str
    target_qty: int
    count: int = 0
    size: int = 0
    start_time: float = field(default_factory=perf_counter)

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

    @property
    def report_str(self) -> str:
        """Get the report string."""
        return get_report(self.path, self.size_str, self.runtime_str, self.count, self.target_qty)

    def accept(self, e: FSEntry) -> None:
        """Update the directory stats after accepting a file."""
        self.count += 1
        self.size += e.size


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
