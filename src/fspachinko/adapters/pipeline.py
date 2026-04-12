"""Model classes for the domain."""

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from itertools import islice
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from concurrent.futures import Future, ThreadPoolExecutor

    from fspachinko.domain.model import DestinationDirectory, FSEntry

_MAX_CHUNK_SIZE = 32


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
    def _walk_parallel(self, executor: ThreadPoolExecutor) -> Iterator[FSEntry]:
        """Walk the source directory and yield FSEntry objects."""

    @abstractmethod
    def walk(self, executor: ThreadPoolExecutor) -> Iterator[FSEntry]:
        """Walk filtered entries."""

    @abstractmethod
    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""

    @abstractmethod
    def transfer_file(self, src: str, dst: str) -> None:
        """Transfer a file from source to destination."""


class TransferPipeline(AbstractPipeline):
    """Owns the strategy objects — Engine delegates to this."""

    def _walk_parallel(self, executor: ThreadPoolExecutor) -> Iterator[FSEntry]:
        """Walk the source directory and yield FSEntry objects."""
        src = self.walker_fn()
        pending: deque[tuple[FSEntry, Future[float]]] = deque()

        def fill() -> None:
            for entry in islice(src, _MAX_CHUNK_SIZE - len(pending)):
                future = executor.submit(self.duration_fn, entry.path)
                pending.append((entry, future))

        fill()
        while pending:
            entry, fut = pending.popleft()
            fill()
            entry.duration = fut.result()
            yield entry

    def walk(self, executor: ThreadPoolExecutor) -> Iterator[FSEntry]:
        """Walk filtered entries."""
        src = self._walk_parallel(executor)
        pending: deque[tuple[FSEntry, Future[bool]]] = deque()

        def fill() -> None:
            for entry in islice(src, _MAX_CHUNK_SIZE - len(pending)):
                future = executor.submit(self.filefilter_fn, entry)
                pending.append((entry, future))

        fill()
        while pending:
            entry, fut = pending.popleft()
            fill()
            if fut.result():
                yield entry

    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""
        return self.get_new_path_fn(dst, e)

    def transfer_file(self, src: str, dst: str) -> None:
        """Transfer a file from source to destination."""
        self.transfer_fn(src, dst)
