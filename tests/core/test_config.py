"""Tests for pydantic config."""

from os.path import realpath

import pytest
from pydantic import ValidationError

from fspachinko.config import ConfigModel, DirectoryModel, FilecountModel, FilenameModel, OptionsModel, RangeFilterModel


def test_filecount_model() -> None:
    """Test FilecountModel validation."""
    # Test valid model
    m = FilecountModel(count=5, is_rand_enabled=True, rand_min=1, rand_max=10)
    assert m.count == 5
    assert m.is_rand_enabled is True
    assert m.rand_min == 1
    assert m.rand_max == 10

    with pytest.raises(ValidationError, check=lambda e: "count" in str(e)):
        m = FilecountModel(count=0, is_rand_enabled=True, rand_min=1, rand_max=10)

    with pytest.raises(ValidationError, check=lambda e: "rand_min" in str(e)):
        m = FilecountModel(count=5, is_rand_enabled=True, rand_min=0, rand_max=10)

    with pytest.raises(ValidationError, check=lambda e: "rand_max" in str(e)):
        m = FilecountModel(count=5, is_rand_enabled=True, rand_min=1, rand_max=0)

    with pytest.raises(ValueError, check=lambda e: "Random minimum cannot be greater than random maximum" in str(e)):
        m = FilecountModel(count=5, is_rand_enabled=True, rand_min=10, rand_max=1)


def test_directory_model() -> None:
    """Test DirectoryModel validation."""
    # Test valid model
    m = DirectoryModel(is_enabled=True, name="test_dir", count=5)
    assert m.is_enabled is True
    assert m.name == "test_dir"
    assert m.count == 5

    # Test count validation
    m = DirectoryModel(is_enabled=True, name="test_dir", count=0)
    assert m.count == 1

    # Test disabling directory creation resets count to 1
    m = DirectoryModel(is_enabled=False, name="test_dir", count=5)
    assert m.is_enabled is False
    assert m.count == 1


def test_filename_model() -> None:
    """Test FilenameModel validation."""
    # Test valid model
    m = FilenameModel(is_enabled=True, template="{original}_{index}")
    assert m.is_enabled is True
    assert m.template == "{original}_{index}"

    # Test empty template validation
    m = FilenameModel(is_enabled=True, template="   ")
    assert m.template == "{original}"


def test_rangefilter_model() -> None:
    """Test RangeFilterModel validation."""
    # Test valid model
    m = RangeFilterModel(is_enabled=True, minimum=100, maximum=1000)
    assert m.is_enabled is True
    assert m.minimum == 100
    assert m.maximum == 1000

    # Test minimum validation
    m = RangeFilterModel(is_enabled=True, minimum=-1, maximum=1000)
    assert m.minimum == 0

    # Test maximum validation
    m = RangeFilterModel(is_enabled=True, minimum=100, maximum=-1)
    assert m.maximum == float("inf")

    # Test minimum greater than maximum validation
    with pytest.raises(ValueError, check=lambda e: "Minimum cannot be greater than maximum." in str(e)):
        m = RangeFilterModel(is_enabled=True, minimum=1000, maximum=100)


def test_options_model() -> None:
    """Test OptionsModel validation."""
    # Test valid model
    m = OptionsModel(transfer_mode="copy", rng_seed=42, max_per_dir=5, is_create_unique_dirs=True)
    assert m.transfer_mode == "copy"
    assert m.rng_seed == 42
    assert m.max_per_dir == 5
    assert m.is_create_unique_dirs is True

    # Test max_per_dir validation
    m = OptionsModel(transfer_mode="copy", rng_seed=42, max_per_dir=-1, is_create_unique_dirs=True)
    assert m.max_per_dir == float("inf")

    # Test rng_seed validation
    m = OptionsModel(transfer_mode="copy", rng_seed="", max_per_dir=5, is_create_unique_dirs=True)
    assert m.rng_seed is None


def test_config_model() -> None:
    """Test ConfigModel validation."""
    # Test valid model
    m = ConfigModel(root="/source", dest="/destination")
    assert m.root == realpath("/source")
    assert m.dest == realpath("/destination")

    m = ConfigModel(root="C:/source", dest="C:/destination")
    assert m.root == "C:/source"
    assert m.dest == "C:/destination"
