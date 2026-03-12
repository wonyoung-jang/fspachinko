"""Tests for filenamer.py."""

import os

from fspachinko.adapters.dirnamer import StaticDirectoryNamer, UniqueDirectoryNamer
from fspachinko.adapters.filecounter import RandomFileCounter, StaticFileCounter
from fspachinko.adapters.filenamer import StaticFilenamer, TemplateFilenamer
from fspachinko.adapters.transfer import AbstractTransfer
from fspachinko.constants import FilenameTemplate, TransferMode
from fspachinko.service.handlers import get_dirname_fn, get_filecount_fn, get_filenamer_fn, get_transfer_fn


def test_get_filenamer_fn() -> None:
    """Test get_filenamer_fn."""
    filenamer = get_filenamer_fn(template=" ", is_enabled=False)
    assert isinstance(filenamer, StaticFilenamer)

    filenamer = get_filenamer_fn(template=FilenameTemplate.ORIGINAL, is_enabled=True)
    assert isinstance(filenamer, StaticFilenamer)

    filenamer = get_filenamer_fn(template="{original}_{index}", is_enabled=True)
    assert isinstance(filenamer, TemplateFilenamer)


def test_get_dirname_fn() -> None:
    """Test get_dirname_fn."""
    dirname_fn = get_dirname_fn(dest="dest", name="", is_enabled=False)
    assert isinstance(dirname_fn, StaticDirectoryNamer)
    assert dirname_fn.gen_dir_name() == "dest"

    dirname_fn = get_dirname_fn(dest="dest", name="test", is_enabled=True)
    assert isinstance(dirname_fn, UniqueDirectoryNamer)
    assert dirname_fn.gen_dir_name() == os.path.join("dest", "test")


def test_get_filecount_fn() -> None:
    """Test get_filecount_fn."""
    filecount_fn = get_filecount_fn(count=5, rand_min=1, rand_max=10, is_rand_enabled=False)
    assert isinstance(filecount_fn, StaticFileCounter)
    assert filecount_fn.gen_file_count() == 5

    filecount_fn = get_filecount_fn(count=5, rand_min=1, rand_max=10, is_rand_enabled=True)
    assert isinstance(filecount_fn, RandomFileCounter)
    assert 1 <= filecount_fn.gen_file_count() <= 10


def test_get_transfer_fn() -> None:
    """Test get_transfer_fn."""
    for mode in TransferMode:
        transfer_fn = get_transfer_fn(mode.value)
        assert transfer_fn is not None
        assert isinstance(transfer_fn, AbstractTransfer)
