"""Tests for filenamer.py."""

from fspachinko.core.config import DirectoryModel, FilecountModel, FilenameModel
from fspachinko.core.constants import FilenameTemplate
from fspachinko.core.verbs.dirnamer import StaticDirectoryNamer, UniqueDirectoryNamer, get_dirname_fn
from fspachinko.core.verbs.filecounter import FixedFileCounter, RandomFileCounter, get_filecount_fn
from fspachinko.core.verbs.filenamer import StaticFilenamer, TemplateFilenamer, get_filenamer_fn
from fspachinko.core.verbs.transfer import AbstractTransfer, TransferMode, get_transfer_fn


def test_get_filenamer_fn() -> None:
    """Test get_filenamer_fn."""
    m = FilenameModel(is_enabled=False, template="")
    filenamer = get_filenamer_fn(m)
    assert isinstance(filenamer, StaticFilenamer)

    m = FilenameModel(is_enabled=True, template=FilenameTemplate.ORIGINAL)
    filenamer = get_filenamer_fn(m)
    assert isinstance(filenamer, StaticFilenamer)

    m = FilenameModel(is_enabled=True, template="{original}_{index}")
    filenamer = get_filenamer_fn(m)
    assert isinstance(filenamer, TemplateFilenamer)


def test_get_dirname_fn() -> None:
    """Test get_dirname_fn."""
    m = DirectoryModel(is_enabled=False, name="")
    dirname_fn = get_dirname_fn(m, dest="dest")
    assert isinstance(dirname_fn, StaticDirectoryNamer)
    assert dirname_fn() == "dest"

    m = DirectoryModel(is_enabled=True, name="test")
    dirname_fn = get_dirname_fn(m, dest="dest")
    assert isinstance(dirname_fn, UniqueDirectoryNamer)


def test_get_filecount_fn() -> None:
    """Test get_filecount_fn."""
    m = FilecountModel(is_rand_enabled=False, count=5, rand_min=1, rand_max=10)
    filecount_fn = get_filecount_fn(m)
    assert isinstance(filecount_fn, FixedFileCounter)
    assert filecount_fn() == 5

    m = FilecountModel(is_rand_enabled=True, count=5, rand_min=1, rand_max=10)
    filecount_fn = get_filecount_fn(m)
    assert isinstance(filecount_fn, RandomFileCounter)
    assert 1 <= filecount_fn() <= 10


def test_get_transfer_fn() -> None:
    """Test get_transfer_fn."""
    for mode in TransferMode:
        transfer_fn = get_transfer_fn(mode.value)
        assert transfer_fn is not None
        assert isinstance(transfer_fn, AbstractTransfer)
