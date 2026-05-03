"""All adapters related to system operations."""

import contextlib
import json
import logging
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from filecmp import cmp
from functools import cache
from io import UnsupportedOperation
from os import link, mkdir, scandir, symlink, unlink
from os.path import basename, join, splitext
from shutil import copy, copy2, move
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from fspachinko.domain.model import FSEntry, FSPachinkoPin
from fspachinko.fp import Fp

if TYPE_CHECKING:
    import random
    from collections.abc import Callable, Iterable, Iterator, Sequence


logger = logging.getLogger(__name__)


class AbstractFilesystem(ABC):
    """Abstract interface for filesystem operations."""

    @abstractmethod
    def get_unique_path(self, path: str, existing: Iterable[str]) -> str:
        """Get a new path, ensuring it doesn't already exist."""

    @abstractmethod
    def are_files_identical(self, f1: str, f2: str) -> bool:
        """Check if two files are identical by comparing their contents."""

    @abstractmethod
    def get_existing_json_files(self, path: str) -> list[str]:
        """Get a list of existing JSON file paths within the specified path."""

    @abstractmethod
    def get_existing_files_for_existing_dest(self, path: str) -> Iterator[tuple[str, int]]:
        """Get a dictionary of existing file paths and their sizes within the specified path."""

    @abstractmethod
    def get_existing_subdirs(self, path: str) -> set[str]:
        """Get a set of existing directory paths within the specified path."""

    @abstractmethod
    def join_path(self, *parts: str) -> str:
        """Join path parts into a single path."""

    @abstractmethod
    def json_to_dict(self, path: str) -> dict:
        """Load JSON data from a file."""

    @abstractmethod
    def get_stem_and_ext(self, path: str) -> tuple[str, str]:
        """Get the stem and extension of a file path."""

    @abstractmethod
    def save_json(self, path: str, data: dict) -> None:
        """Save JSON data to a file."""

    @abstractmethod
    def make_directory(self, path: str) -> None:
        """Create a directory at the specified path."""

    @abstractmethod
    def remove_directory(self, path: str) -> None:
        """Remove a directory and its contents, with error handling."""


class Filesystem(AbstractFilesystem):
    """Concrete implementation of AbstractFilesystem using the local filesystem."""

    def get_unique_path(self, path: str, existing: Iterable[str]) -> str:
        """Get a new path, ensuring it doesn't already exist."""
        if path not in existing:
            return path
        stem, _, ext = path.rpartition(".")
        if not stem:
            stem, ext = ext, ""
        else:
            ext = f".{ext}"
        x = 2
        while (candidate := f"{stem} ({x}){ext}") in existing:
            x += 1
        return candidate

    def are_files_identical(self, f1: str, f2: str) -> bool:
        """Check if two files are identical by comparing their contents."""
        try:
            if cmp(f1, f2, shallow=True):
                return cmp(f1, f2, shallow=False)
        except OSError:
            return True
        return False

    def get_existing_json_files(self, path: str) -> list[str]:
        """Get a list of existing JSON file paths within the specified path."""
        return [e.name for e in scandir(path) if self.get_stem_and_ext(e.name)[1].lower() == ".json"]

    def get_existing_files_for_existing_dest(self, path: str) -> Iterator[tuple[str, int]]:
        """Get a set of existing file paths within the specified path."""
        yield from ((e.path, e.stat().st_size) for e in scandir(path) if e.is_file())

    def get_existing_subdirs(self, path: str) -> set[str]:
        """Get a set of existing directory paths within the specified path."""
        return {e.path for e in scandir(path) if e.is_dir()}

    def join_path(self, *parts: str) -> str:
        """Join path parts into a single path."""
        return join(*parts)

    def json_to_dict(self, path: str) -> dict:
        """Load JSON data from a file."""
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except OSError:
            return {}

    def get_stem_and_ext(self, path: str) -> tuple[str, str]:
        """Get the stem and extension of a file path."""
        return splitext(basename(path))

    def save_json(self, path: str, data: dict) -> None:
        """Save JSON data to a file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def remove_directory(self, path: str) -> None:
        """Remove a directory and its contents, with error handling."""
        shutil.rmtree(path)

    def make_directory(self, path: str) -> None:
        """Create a directory at the specified path."""
        mkdir(path)


@dataclass(slots=True)
class AbstractFSWalker(ABC):
    """Abstract class for filesystem walker."""

    root: str
    should_follow_symlink: bool
    rng: random.Random

    @abstractmethod
    def __call__(self) -> Iterator[FSEntry]:
        """Walk the filesystem and return an iterator of FSEntry objects."""


@dataclass(slots=True)
class FSWalker(AbstractFSWalker):
    """Filesystem walker implementation."""

    _board: dict[str, FSPachinkoPin] = field(default_factory=dict)

    def __call__(self) -> Iterator[FSEntry]:
        """Walk the filesystem and return an iterator of FSEntry objects."""
        _starting_parent_curr_pair = ("", self.root)
        _parent, _curr = _starting_parent_curr_pair
        _board = self._board
        _pop = _board.pop
        _randint = self.rng.randint
        _random = self.rng.random
        _choice = self.rng.choice
        while True:
            pin = self.pin_from_path(_curr)
            if len(pin) == 0:
                if _curr == self.root:
                    return
                _pop(_curr)
                if _parent in _board:
                    with contextlib.suppress(ValueError):
                        _board[_parent].subdirs.remove(_curr)
                _parent, _curr = _starting_parent_curr_pair
                continue
            if _random() < pin.subdir_total_ratio:  # Should descend
                _parent, _curr = (_curr, _choice(pin.subdirs))
                continue
            if files := pin.files:
                idx = _randint(0, len(files) - 1)
                yield files.pop(idx)
            _parent, _curr = _starting_parent_curr_pair

    def pin_from_path(self, path: str) -> FSPachinkoPin:
        """Add a new pin to the board, or return an existing one."""
        if path in self._board:
            return self._board[path]
        self._board[path] = pin = FSPachinkoPin(path=path)
        self.scan_pin(pin)
        return pin

    def scan_pin(self, pin: FSPachinkoPin) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        try:
            with scandir(pin.path) as it:
                follow = self.should_follow_symlink
                append_subdir = pin.subdirs.append
                append_file = pin.files.append
                parent = pin.path
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=follow):
                            append_subdir(e.path)
                        elif e.is_file(follow_symlinks=follow):
                            stat = e.stat(follow_symlinks=follow)
                            stem, sep, ext = e.name.rpartition(".")
                            if not sep:
                                stem, ext = ext, ""
                            else:
                                ext = f".{ext}"
                            append_file(
                                FSEntry(
                                    path=e.path,
                                    stem=stem,
                                    ext=ext,
                                    parent=parent,
                                    size=stat.st_size,
                                    mtime=stat.st_mtime_ns,
                                ),
                            )
                    except OSError:
                        logger.debug("Error accessing entry %s, skipping.", e.path)
        except OSError:
            logger.debug("Error scanning directory %s, skipping.", pin.path)


FFPROBE_TIMEOUT = 2
FFPROBE_DURATION_CMD: Sequence[str] = (
    "ffprobe",
    "-v",
    "error",
    "-show_entries",
    "format=duration",
    "-of",
    "default=noprint_wrappers=1:nokey=1",
)


@cache
def get_duration_ffprobe(path: str) -> float:
    """Get the duration of a media file."""
    try:
        result = subprocess.run(
            args=[*FFPROBE_DURATION_CMD, path],
            timeout=FFPROBE_TIMEOUT,
            capture_output=True,
            check=True,
            encoding="utf-8",
        )
        dur = float(result.stdout.strip())
    except ValueError, subprocess.SubprocessError:
        dur = Fp.MAXFLOAT
    return dur


def get_duration_null(_: str) -> float:
    """Fallback duration function that returns infinity."""
    return Fp.MAXFLOAT


def duration_fn_factory() -> Callable[[str], float]:
    """Create a get_duration function based on ffprobe availability."""
    if not shutil.which("ffprobe"):
        logger.warning("ffprobe not found in system PATH. Cannot evaluate media duration.")
        return get_duration_null
    return get_duration_ffprobe


FILENAME_TEMPLATE_MAP: dict[Fp.FilenameTemplate, Callable[[FSEntry, int], str | int]] = {
    Fp.FilenameTemplate.ORIGINAL: lambda e, _: e.stem,
    Fp.FilenameTemplate.INDEX: lambda _, c: c + 1,
    Fp.FilenameTemplate.PARENT: lambda e, _: basename(e.parent),
}


@cache
def _available_filename_map(template: str) -> dict[str, Callable[[FSEntry, int], str | int]]:
    """Get the mapping of available filename template variables."""
    return {templ: fn for templ, fn in FILENAME_TEMPLATE_MAP.items() if templ in template}


@dataclass(slots=True)
class AbstractFilenamer(ABC):
    """Abstract filenamer."""

    template: str

    @abstractmethod
    def __call__(self, entry: FSEntry, count: int) -> str:
        """Generate a filename."""


@dataclass(slots=True)
class TemplateFilenamer(AbstractFilenamer):
    """Filenamer that generates filenames based on templates."""

    _map: dict[str, Callable[[FSEntry, int], str | int]] = field(init=False)

    def __post_init__(self) -> None:
        """Validate the template."""
        self._map = _available_filename_map(self.template)

    def __call__(self, entry: FSEntry, count: int) -> str:
        """Generate a filename based on the specified template."""
        try:
            mapping = {templ: fn(entry, count) for templ, fn in self._map.items()}
            return self.template.format_map(mapping)
        except KeyError, ValueError, IndexError:
            return entry.stem


def _link_fn_is_available(link_fn: Callable) -> bool:
    """Test if a link function works in the current environment."""
    try:
        with TemporaryDirectory(delete=True) as tmpdir:
            test_src = join(tmpdir, "test_src")
            test_link = join(tmpdir, "test_link")
            open(test_src, "w").close()
            link_fn(test_src, test_link)
            unlink(test_link)
            unlink(test_src)
    except OSError, UnsupportedOperation, NotImplementedError:
        return False
    return True


def hardlink(src: str, dst: str) -> None:
    """Create a hardlink from source to destination."""
    try:
        link(src, dst)
    except OSError as e:
        if e.errno == 18:  # Invalid cross-device link
            symlink(src, dst)
        else:
            raise


_TRANSFER_FNS: dict[Fp.TransferMode, Callable] = {
    Fp.TransferMode.DRY_RUN: lambda _, __: None,
    Fp.TransferMode.COPY: copy,
    Fp.TransferMode.COPY_PRESERVE: copy2,
    Fp.TransferMode.MOVE: move,
    Fp.TransferMode.SYMLINK: symlink,
    Fp.TransferMode.HARDLINK: hardlink,
}

_LINK_FNS: dict[Fp.TransferMode, Callable] = {
    Fp.TransferMode.SYMLINK: symlink,
    Fp.TransferMode.HARDLINK: link,
}


@cache
def available_transfer_fn_factory() -> dict[Fp.TransferMode, Callable]:
    """Create a transfer function manager."""
    _transfer_fns = _TRANSFER_FNS.copy()
    for mode, fn in _LINK_FNS.items():
        if not _link_fn_is_available(fn):
            _transfer_fns.pop(mode, None)
    return _transfer_fns


@cache
def get_transfer_fn(mode: str) -> Callable[[str, str], None]:
    """Get the transfer function for the specified mode."""
    _available = available_transfer_fn_factory()
    return _available.get(Fp.TransferMode(mode), _available[Fp.TransferMode.DRY_RUN])
