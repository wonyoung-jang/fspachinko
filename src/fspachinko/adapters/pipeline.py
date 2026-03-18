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
    filefilter_fn: Callable = lambda _: True
    filenamer_fn: Callable[[FSEntry, int], str] = lambda _, __: ""
    transfer_fn: Callable = lambda _: True
    walker_fn: Callable[[], Iterator[FSEntry]] = lambda: iter(())
    filecount_fn: Callable = lambda _: True
    dirname_fn: Callable = lambda _: True

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
        d = self.dirname_fn()
        if self.is_create_dir:
            return get_dest_dir_path(d)
        return d

    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""
        new_stem = self.filenamer_fn(e, dst.count)
        ext = e.ext.casefold()
        target = join(dst.path, f"{new_stem}{ext}")
        if are_files_equal(e.path, target):
            return None
        return get_unique_path(dst.path, new_stem, ext)
