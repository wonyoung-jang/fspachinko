"""Model classes for the domain."""

from abc import ABC, abstractmethod
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from itertools import islice
from typing import TYPE_CHECKING

from fspachinko.adapters.duration import get_duration_null
from fspachinko.domain.events import Event, FileTransferred
from fspachinko.fp import Fp

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from concurrent.futures import Future

    from fspachinko.adapters.cache import AbstractMetadataCache
    from fspachinko.domain.model import DestinationDirectory, FSEntry, TransferJob


def prefetch(src: Iterator[FSEntry], submit: Callable) -> Iterator[tuple[FSEntry, Future]]:
    """Prefetch entries."""
    pending: deque[tuple[FSEntry, Future]] = deque()

    def fill(submit: Callable = submit) -> None:
        pending.extend((e, submit(e)) for e in islice(src, Fp.MAXCHUNK - len(pending)))

    fill()
    while pending:
        yield pending.popleft()
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
    def transfer_dir(self, job: TransferJob, dst: DestinationDirectory) -> Iterator[Event]:
        """Transfer files to a destination directory."""


class TransferPipeline(AbstractPipeline):
    """Owns the strategy objects — Engine delegates to this."""

    def transfer_dir(self, job: TransferJob, dst: DestinationDirectory) -> Iterator[Event]:
        """Transfer files to a destination directory."""
        with ThreadPoolExecutor() as executor:
            yield from self._transfer_dir(executor, job, dst)

    def _transfer_dir(
        self, executor: ThreadPoolExecutor, job: TransferJob, dst: DestinationDirectory
    ) -> Iterator[Event]:
        """Transfer files to a destination directory."""
        src = self._walk_filter(executor)
        futures: dict[Future[None], FileTransferred] = {}

        def fill() -> None:
            for entry in src:
                if dst.is_success or job.is_stop_condition:
                    break
                if not job.can_accept(entry):
                    continue
                if (newpath := self.get_new_path_fn(dst, entry)) is None:
                    continue
                dst.add(newpath, entry.size)
                job.register_transfer(entry)
                future = executor.submit(self.transfer_fn, entry.path, newpath)
                futures[future] = FileTransferred(src=entry.path, dst=newpath)

        fill()
        while futures:
            fut = next(as_completed(futures))
            fut.result()
            yield futures.pop(fut)
            if job.is_stop_condition:
                for f in futures:
                    f.cancel()
                break
            fill()

    def _walk_filter(self, executor: ThreadPoolExecutor) -> Iterator[FSEntry]:
        """Walk filtered entries."""

        def submit(e: FSEntry) -> Future[bool]:
            return executor.submit(self.filefilter_fn, e)

        no_dur_fn = self.duration_fn is get_duration_null
        src = self.walker_fn() if no_dur_fn else self._walk_ffprobe(executor)

        for e, fut in prefetch(src=src, submit=submit):
            if fut.result():
                yield e

    def _walk_ffprobe(self, executor: ThreadPoolExecutor) -> Iterator[FSEntry]:
        """Walk and probe durations."""
        cache = self.cache

        def submit(e: FSEntry) -> Future[float] | None:
            if cache and (dur := cache.get_duration(e)) is not None:
                e.duration = dur
                return None
            return executor.submit(self.duration_fn, e.path)

        for e, fut in prefetch(src=self.walker_fn(), submit=submit):
            if fut is not None:
                e.duration = fut.result()
                if cache is not None:
                    cache.set_entry(e)
            yield e
