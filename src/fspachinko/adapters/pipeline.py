"""Model classes for the domain."""

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from itertools import islice
from typing import TYPE_CHECKING

from fspachinko.adapters.duration import get_duration_null
from fspachinko.fp import Fp

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from concurrent.futures import Future, ThreadPoolExecutor

    from fspachinko.adapters.cache import AbstractMetadataCache
    from fspachinko.domain.model import DestinationDirectory, FSEntry


@dataclass(slots=True)
class AbstractPipeline(ABC):
    """Abstract pipeline."""

    filefilter_fn: Callable[[FSEntry], bool] = lambda _: True
    get_new_path_fn: Callable[[DestinationDirectory, FSEntry], str | None] = lambda _, e: e.stem
    transfer_fn: Callable[[str, str], None] = lambda _, __: None
    walker_fn: Callable[[], Iterator[FSEntry]] = lambda: iter(())
    duration_fn: Callable[[str], float] = get_duration_null
    inputs: deque[tuple[str, int, bool]] = field(default_factory=deque)
    cache: AbstractMetadataCache | None = None

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


@dataclass(slots=True)
class TransferPipeline(AbstractPipeline):
    """Owns the strategy objects — Engine delegates to this."""

    def _walk_parallel(self, executor: ThreadPoolExecutor) -> Iterator[FSEntry]:
        """Walk the source directory and yield FSEntry objects."""
        src = self.walker_fn()
        pending: deque[tuple[FSEntry, Future[float] | None]] = deque()
        no_dur_fn = getattr(self.duration_fn, "__name__", None) == "get_duration_null"

        def _fill() -> None:
            for e in islice(src, Fp.MAXCHUNK - len(pending)):
                if no_dur_fn:
                    pending.append((e, None))
                elif self.cache and (dur := self.cache.get_duration(e)):
                    e.duration = dur
                    pending.append((e, None))
                else:
                    future = executor.submit(self.duration_fn, e.path)
                    pending.append((e, future))

        _fill()
        while pending:
            e, fut = pending.popleft()
            _fill()
            if fut is not None:
                e.duration = fut.result()
                if self.cache is not None:
                    self.cache.set_entry(e)
            yield e

    def walk(self, executor: ThreadPoolExecutor) -> Iterator[FSEntry]:
        """Walk filtered entries."""
        src = self._walk_parallel(executor)
        pending: deque[tuple[FSEntry, Future[bool]]] = deque()

        def _fill() -> None:
            for e in islice(src, Fp.MAXCHUNK - len(pending)):
                future = executor.submit(self.filefilter_fn, e)
                pending.append((e, future))

        _fill()
        while pending:
            e, fut = pending.popleft()
            _fill()
            if fut.result():
                yield e

    def get_new_path(self, dst: DestinationDirectory, e: FSEntry) -> str | None:
        """Check if the original file name can be used without transfer."""
        return self.get_new_path_fn(dst, e)

    def transfer_file(self, src: str, dst: str) -> None:
        """Transfer a file from source to destination."""
        self.transfer_fn(src, dst)
