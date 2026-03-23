"""Model classes for the domain."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from filecmp import cmp
from os.path import join
from typing import TYPE_CHECKING

from .filesystemport import get_unique_path

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from fspachinko.domain.model import DestinationDirectory, FSEntry


@dataclass(slots=True)
class AbstractPipeline(ABC):
    """Abstract pipeline."""

    is_create_dir: bool = False
    filters: dict[str, Callable] = field(default_factory=dict)
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
        target = join(dst.path, f"{new_stem}{ext}")
        if target not in dst.files:
            return target
        # If the file already exists and is the same, skip transferring it.
        if cmp(e.path, target, shallow=True) and cmp(e.path, target, shallow=False):
            return None
        return get_unique_path(target, dst.files)
