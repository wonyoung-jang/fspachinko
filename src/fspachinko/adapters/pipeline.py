"""Model classes for the domain."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from fspachinko.domain.model import DestinationDirectory, FSEntry


@dataclass(slots=True)
class AbstractPipeline(ABC):
    """Abstract pipeline."""

    filefilter_fn: Callable[[FSEntry], bool] = lambda _: True
    get_new_path_fn: Callable[[DestinationDirectory, FSEntry], str | None] = lambda _, e: e.stem
    transfer_fn: Callable[[str, str], None] = lambda _, __: None
    walker_fn: Callable[[], Iterator[FSEntry]] = lambda: iter(())

    @abstractmethod
    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""


class TransferPipeline(AbstractPipeline):
    """Owns the strategy objects — Engine delegates to this."""

    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""
        return self.get_new_path_fn(dst, e)
