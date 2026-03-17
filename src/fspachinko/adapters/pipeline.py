"""Model classes for the domain."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from os.path import join
from typing import TYPE_CHECKING

from .filesystemport import are_files_equal, get_dest_dir_path, get_unique_path

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from ..domain.model import DestinationDirectory, FSEntry


@dataclass(slots=True)
class AbstractPipeline(ABC):
    """Abstract pipeline."""

    is_create_dir: bool = False
    filter_file: Callable = lambda _: True
    get_file_stem: Callable = lambda _: True
    transfer: Callable = lambda _: True
    walk: Callable[[], Iterator[FSEntry]] = lambda: iter(())
    get_target_filecount: Callable = lambda _: True
    get_directory_name: Callable = lambda _: True

    @abstractmethod
    def get_currdir_dest(self) -> str:
        """Get the current directory destination."""

    @abstractmethod
    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""


class TransferPipeline(AbstractPipeline):
    """Owns the strategy objects — Engine delegates to this."""

    def get_currdir_dest(self) -> str:
        """Get the current directory destination."""
        d = self.get_directory_name()
        if self.is_create_dir:
            return get_dest_dir_path(d)
        return d

    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""
        new_stem = self.get_file_stem(e, dst.count)
        ext = e.ext.casefold()
        target = join(dst.path, f"{new_stem}{ext}")
        if are_files_equal(e.path, target):
            return None
        return get_unique_path(dst.path, new_stem, ext)
