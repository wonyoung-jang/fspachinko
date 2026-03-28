"""Model classes for the domain."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .filesystem import AbstractFilesystem, Filesystem

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from fspachinko.domain.model import DestinationDirectory, FSEntry


@dataclass(slots=True)
class AbstractPipeline(ABC):
    """Abstract pipeline."""

    filesystem: AbstractFilesystem = field(default_factory=Filesystem)
    is_create_dir: bool = False
    filefilter_fn: Callable[[FSEntry], bool] = lambda _: True
    filenamer_fn: Callable[[FSEntry, int], str] = lambda e, _: e.stem
    transfer_fn: Callable[[str, str], None] = lambda _, __: None
    walker_fn: Callable[[], Iterator[FSEntry]] = lambda: iter(())
    dest_dir_inputs: list[tuple[str, int]] = field(default_factory=list)

    @abstractmethod
    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""


class TransferPipeline(AbstractPipeline):
    """Owns the strategy objects — Engine delegates to this."""

    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""
        new_stem = self.filenamer_fn(e, dst.count)
        ext = e.ext.casefold()
        target = self.filesystem.join_path(dst.path, f"{new_stem}{ext}")
        if target not in dst.files:
            return target
        # If the file already exists and is the same, skip transferring it.
        if self.filesystem.are_files_identical(e.path, target):
            return None
        return self.filesystem.get_unique_path(target, dst.files)
