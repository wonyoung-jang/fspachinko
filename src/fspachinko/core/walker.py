"""Random file system navigator."""

from dataclasses import dataclass, field
from os import scandir
from os.path import basename, dirname, splitext
from random import choice
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(slots=True, frozen=True)
class FSEntry:
    """Lightweight wrapper for os.DirEntry."""

    path: str
    stem: str
    ext: str
    parent: str
    size: int

    def __fspath__(self) -> str:
        """Return the file system path representation."""
        return self.path


@dataclass(slots=True)
class FSPachinkoPin:
    """Represents a 'pin' on the Pachinko board."""

    path: str
    follow: bool
    subdirs: list[str] = field(default_factory=list)
    files: list[FSEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Only look at the OS file system when a ball hits a specific folder for the first time."""
        try:
            with scandir(self.path) as it:
                follow = self.follow
                subdirs_append = self.subdirs.append
                files_append = self.files.append
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=follow):
                            subdirs_append(e.path)
                        elif e.is_file(follow_symlinks=follow):
                            stem, ext = splitext(e.name)
                            files_append(
                                FSEntry(
                                    path=e.path,
                                    stem=stem,
                                    ext=ext,
                                    parent=basename(dirname(e.path)),
                                    size=e.stat(follow_symlinks=follow).st_size,
                                )
                            )
                    except OSError:
                        continue
        except OSError:
            return


class FSWalker:
    """Abstract file system walker."""

    def __call__(self) -> Iterator[FSEntry]:
        """Generate candidates for a given directory."""
        msg = "FSWalker is an abstract class and cannot be called directly."
        raise NotImplementedError(msg)


@dataclass(slots=True)
class PachinkoFSWalker(FSWalker):
    """Simulates a Pachinko machine.

    For every file needed, we 'drop' a search cursor from the Root.
    It bounces randomly down directory paths until it settles on a file.
    """

    root: str
    should_follow_symlink: bool
    board: dict[str, FSPachinkoPin] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize the board with the root pin."""
        self.board[self.root] = FSPachinkoPin(self.root, self.should_follow_symlink)

    def __call__(self) -> Iterator[FSEntry]:
        """Iterate through FSEntry objects."""
        root = self.root
        curr = self.root
        board_setdefault = self.board.setdefault
        follow = self.should_follow_symlink

        while root in self.board:
            pin = board_setdefault(curr, FSPachinkoPin(curr, follow))
            subdirs, files = pin.subdirs, pin.files

            if not subdirs and not files:
                if curr == root:
                    break
                curr = root
                continue

            should_descend = choice((True, False)) if subdirs and files else bool(subdirs)
            if should_descend:
                curr = choice(subdirs)
                continue

            if files:
                yield choice(files)

            curr = root
