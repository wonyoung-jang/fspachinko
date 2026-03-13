"""Model classes for the domain."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from os.path import join
from typing import TYPE_CHECKING

from .filesystemport import are_files_equal, get_dest_dir_path, get_unique_path, remove_directory

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..adapters.walker import AbstractFSWalker
    from ..domain.model import DestinationDirectory, FSEntry


@dataclass(slots=True)
class AbstractPipeline(ABC):
    """Abstract pipeline."""

    is_create_dir: bool
    filefilter_fn: Callable
    filenamer_fn: Callable
    transfer_fn: Callable
    walker_fn: AbstractFSWalker
    filecount_fn: Callable
    dirname_fn: Callable

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

    def get_currdir_dest(self) -> str:
        """Get the current directory destination."""
        d = self.dirname_fn()
        match self.is_create_dir:
            case True:
                return get_dest_dir_path(d)
            case False:
                return d

    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""
        ext = e.ext.casefold()
        new_stem = self.filenamer_fn(e, dst.count)
        target = join(dst.path, f"{new_stem}{ext}")
        if are_files_equal(e.path, target):
            return None
        return get_unique_path(dst.path, new_stem, ext)

    def remove_dst_dir_if_empty(self, path: str, *, is_empty_creation: bool) -> None:
        """Remove the destination directory if it is empty."""
        if is_empty_creation:
            remove_directory(path)
