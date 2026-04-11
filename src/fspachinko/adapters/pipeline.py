"""Model classes for the domain."""

from abc import ABC, abstractmethod
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
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
    duration_fn: Callable[[str], float] = lambda _: float("inf")
    inputs: deque[tuple[str, int, bool]] = field(default_factory=deque)

    @abstractmethod
    def filter_file(self, e: FSEntry) -> bool:
        """Check if a file should be processed."""

    @abstractmethod
    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""

    @abstractmethod
    def transfer_file(self, src: str, dst: str) -> None:
        """Transfer a file from source to destination."""

    @abstractmethod
    def walk(self) -> Iterator[FSEntry]:
        """Walk the source directory and yield FSEntry objects."""


class TransferPipeline(AbstractPipeline):
    """Owns the strategy objects — Engine delegates to this."""

    def filter_file(self, e: FSEntry) -> bool:
        """Check if a file should be processed."""
        return self.filefilter_fn(e)

    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""
        return self.get_new_path_fn(dst, e)

    def transfer_file(self, src: str, dst: str) -> None:
        """Transfer a file from source to destination."""
        self.transfer_fn(src, dst)

    def walk(self) -> Iterator[FSEntry]:
        """Walk the source directory and yield FSEntry objects."""
        with ThreadPoolExecutor(max_workers=32) as executor:
            futures: dict[Future[float], FSEntry] = {}
            for entry in self.walker_fn():
                futures[executor.submit(self.duration_fn, entry.path)] = entry
                done = [f for f in futures if f.done()]
                for f in done:
                    e = futures.pop(f)
                    e.duration = f.result()
                    yield e
            for f in as_completed(futures):
                e = futures.pop(f)
                e.duration = f.result()
                yield e
