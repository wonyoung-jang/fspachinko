"""File transfer adapter."""

from functools import cache
from io import UnsupportedOperation
from os import link, symlink, unlink
from os.path import join
from shutil import copy, copy2, move
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from fspachinko.fp import Fp

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


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


def dry_transfer(_src: str, _dst: str) -> None:
    """Simulate a file transfer without doing anything."""
    return


def hardlink(src: str, dst: str) -> None:
    """Create a hardlink from source to destination."""
    try:
        link(src, dst)
    except OSError as e:
        if e.errno == 18:  # Invalid cross-device link
            symlink(src, dst)
        else:
            raise


_TRANSFER_FNS: dict[str, Callable] = {
    Fp.TransferMode.DRY_RUN: dry_transfer,
    Fp.TransferMode.COPY: copy,
    Fp.TransferMode.COPY_PRESERVE: copy2,
    Fp.TransferMode.MOVE: move,
    Fp.TransferMode.SYMLINK: symlink,
    Fp.TransferMode.HARDLINK: hardlink,
}

_LINK_FNS: dict[str, Callable] = {
    Fp.TransferMode.SYMLINK: symlink,
    Fp.TransferMode.HARDLINK: link,
}


@cache
def available_transfer_fn_factory() -> dict[str, Callable]:
    """Create a transfer function manager."""
    available = _TRANSFER_FNS.copy()
    for mode, fn in _LINK_FNS.items():
        if not _link_fn_is_available(fn):
            available.pop(mode, None)
    return available


@cache
def available_transfer_fns() -> Sequence[str]:
    """Get the available transfer function names."""
    return tuple(available_transfer_fn_factory().keys())
