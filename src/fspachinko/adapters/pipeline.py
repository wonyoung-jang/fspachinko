"""Model classes for the domain."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from os.path import join
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from ..adapters.filesystemport import AbstractFilesystemPort
    from ..adapters.walker import AbstractFSWalker
    from ..domain.model import DestinationDirectory, FSEntry
    from .loggers import AbstractLoggingPort


@dataclass(slots=True)
class AbstractPipeline(ABC):
    """Abstract pipeline."""

    is_create_dir: bool
    fs: AbstractFilesystemPort
    logging: AbstractLoggingPort
    filefilter_fn: Callable
    filenamer_fn: Callable
    transfer_fn: Callable
    walker_fn: AbstractFSWalker
    filecount_fn: Callable
    dirname_fn: Callable

    @abstractmethod
    def walk(self) -> Iterator[FSEntry]:
        """Walk the file system and yield FSEntry objects."""

    @abstractmethod
    def get_file_count(self) -> int:
        """Count the number of files to be transferred."""

    @abstractmethod
    def get_dir_name(self) -> str:
        """Get the name for the current directory."""

    @abstractmethod
    def is_valid(self, e: FSEntry) -> bool:
        """Check if a file should be transferred."""

    @abstractmethod
    def get_new_file_stem(self, e: FSEntry, count: int) -> str:
        """Get the new name for a file."""

    @abstractmethod
    def transfer_file(self, src: str, dst: str) -> None:
        """Transfer a file from src to dst."""

    @abstractmethod
    def add_handler(self, path: str) -> None:
        """Add a logging handler for the current directory."""

    @abstractmethod
    def remove_handler(self) -> None:
        """Remove the logging handler for the current directory."""

    @abstractmethod
    def get_currdir_dest(self) -> str:
        """Get the current directory destination."""

    @abstractmethod
    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""

    @abstractmethod
    def remove_dst_dir_if_empty(self, path: str, *, is_empty_creation: bool) -> None:
        """Remove the destination directory if it is empty."""


class TransferPipeline(AbstractPipeline):
    """Owns the strategy objects — Engine delegates to this."""

    def walk(self) -> Iterator[FSEntry]:
        """Walk the file system and yield FSEntry objects."""
        return self.walker_fn.walk()

    def get_file_count(self) -> int:
        """Count the number of files to be transferred."""
        return self.filecount_fn()

    def get_dir_name(self) -> str:
        """Get the name for the current directory."""
        return self.dirname_fn()

    def is_valid(self, e: FSEntry) -> bool:
        """Check if a file should be transferred."""
        return self.filefilter_fn(e)

    def get_new_file_stem(self, e: FSEntry, count: int) -> str:
        """Get the new name for a file."""
        return self.filenamer_fn(e, count)

    def transfer_file(self, src: str, dst: str) -> None:
        """Transfer a file from src to dst."""
        self.transfer_fn(src, dst)

    def add_handler(self, path: str) -> None:
        """Add a logging handler for the current directory."""
        self.logging.add_handler(path)

    def remove_handler(self) -> None:
        """Remove the logging handler for the current directory."""
        self.logging.remove_handler()

    def get_currdir_dest(self) -> str:
        """Get the current directory destination."""
        d = self.get_dir_name()
        match self.is_create_dir:
            case True:
                return self.fs.get_dest_dir_path(d)
            case False:
                return d

    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""
        ext = e.ext.casefold()
        new_stem = self.get_new_file_stem(e, dst.count)
        target = join(dst.path, f"{new_stem}{ext}")
        if self.fs.are_files_equal(e.path, target):
            return None
        return self.fs.get_unique_path(dst.path, new_stem, ext)

    def remove_dst_dir_if_empty(self, path: str, *, is_empty_creation: bool) -> None:
        """Remove the destination directory if it is empty."""
        if is_empty_creation:
            self.fs.remove_directory(path)
