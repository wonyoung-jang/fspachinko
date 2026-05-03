"""Pipeline adapter for file transfer operations."""

from abc import ABC, abstractmethod
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from itertools import islice
from typing import TYPE_CHECKING

from fspachinko.adapters.system import get_duration_null
from fspachinko.domain.events import Event, FileTransferred
from fspachinko.fp import Fp

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from concurrent.futures import Future

    from fspachinko.adapters.cache import AbstractMetadataCache
    from fspachinko.domain.model import DestinationDirectory, FSEntry, TransferJob


def prefetch(
    src: Iterator[FSEntry], submit: Callable[[FSEntry], Future | None], max_chunk: int = Fp.MAXCHUNK
) -> Iterator[tuple[FSEntry, Future | None]]:
    """Prefetch entries."""
    _pending: deque[tuple[FSEntry, Future | None]] = deque((e, submit(e)) for e in islice(src, max_chunk))
    for e in src:
        yield _pending.popleft()
        _pending.append((e, submit(e)))
    yield from _pending


def run_transfer_dir(
    job: TransferJob, futures: dict[Future[None], FileTransferred], fill: Callable[[], None]
) -> Iterator[Event]:
    """Run the transfer for a destination directory."""
    fill()
    while futures:
        _done, _ = wait(futures, return_when=FIRST_COMPLETED)
        for _fut in _done:
            _fut.result()
            yield futures.pop(_fut)
            if job.is_stop_condition:
                for _f in futures:
                    _f.cancel()
                return
            fill()


@dataclass(slots=True)
class AbstractPipeline(ABC):
    """Abstract pipeline."""

    filefilter_fn: Callable[[FSEntry], bool] = lambda _: True
    get_new_path_fn: Callable[[DestinationDirectory, FSEntry], str | None] = lambda _, e: e.stem
    transfer_fn: Callable[[str, str], None] = lambda _, __: None
    walker_fn: Callable[[], Iterator[FSEntry]] = lambda: iter(())
    duration_fn: Callable[[str], float] = get_duration_null
    inputs: deque[DestinationDirectory] = field(default_factory=deque)
    cache: AbstractMetadataCache | None = None

    @abstractmethod
    def transfer_dir(self, job: TransferJob, dst: DestinationDirectory) -> Iterator[Event]: ...


class TransferPipeline(AbstractPipeline):
    """Owns the strategy objects — Engine delegates to this."""

    def transfer_dir(self, job: TransferJob, dst: DestinationDirectory) -> Iterator[Event]:
        """Transfer files to a destination directory."""
        with ThreadPoolExecutor() as probe_ex, ThreadPoolExecutor() as xfer_ex:
            futures, fill = self._get_futures_and_fill(probe_ex, xfer_ex, job, dst)
            yield from run_transfer_dir(job, futures, fill)

    def _get_futures_and_fill(
        self, probe_ex: ThreadPoolExecutor, xfer_ex: ThreadPoolExecutor, job: TransferJob, dst: DestinationDirectory
    ) -> tuple[dict[Future[None], FileTransferred], Callable[[], None]]:
        """Transfer files to a destination directory."""
        no_dur_fn = self.duration_fn is get_duration_null
        src = self.walker_fn() if no_dur_fn else self._walk_ffprobe(probe_ex)
        futures: dict[Future[None], FileTransferred] = {}

        def fill() -> None:
            while len(futures) < Fp.MAXCHUNK and (entry := next(src, None)) is not None:
                if dst.is_success or job.is_stop_condition:
                    break
                if (
                    not job.can_accept(entry)
                    or not self.filefilter_fn(entry)
                    or (newpath := self.get_new_path_fn(dst, entry)) is None
                ):
                    continue
                dst.add(newpath, entry.size)
                job.register_transfer(entry)
                future = xfer_ex.submit(self.transfer_fn, entry.path, newpath)
                futures[future] = FileTransferred(src=entry.path, dst=newpath)

        return futures, fill

    def _walk_ffprobe(self, probe_ex: ThreadPoolExecutor) -> Iterator[FSEntry]:
        """Walk and probe durations."""
        cache = self.cache
        pending: list[FSEntry] = []

        def submit(e: FSEntry) -> Future[float] | None:
            if cache and (dur := cache.get_duration(e)) is not None:
                e.duration = dur
                return None
            return probe_ex.submit(self.duration_fn, e.path)

        for e, fut in prefetch(src=self.walker_fn(), submit=submit):
            if fut is not None:
                e.duration = fut.result()
                if cache is not None:
                    pending.append(e)
                    if len(pending) >= Fp.MAXCHUNK // 2:
                        cache.set_entries(pending)
                        pending.clear()
            yield e

        if pending and cache is not None:
            cache.set_entries(pending)
