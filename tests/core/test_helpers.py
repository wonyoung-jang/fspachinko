"""Test helper functions."""

from fspachinko.core.constants import StateStatus
from fspachinko.core.helpers import convert_byte_to_human_readable_size, get_report, get_status


def test_convert_byte_to_human_readable_size() -> None:
    """Test convert_byte_to_human_readable_size."""
    assert convert_byte_to_human_readable_size(500) == "500.00 B"
    assert convert_byte_to_human_readable_size(2048) == "2.00 KB"
    assert convert_byte_to_human_readable_size(5 * 1024**2) == "5.00 MB"
    assert convert_byte_to_human_readable_size(3 * 1024**3) == "3.00 GB"


def test_get_status() -> None:
    """Test get_status."""
    assert (
        get_status(
            is_success=True,
            is_none_found=False,
            is_stop_requested=False,
            is_create_dir=False,
            is_root_locked=False,
        )
        == StateStatus.SUCCESS
    )

    assert (
        get_status(
            is_success=False,
            is_none_found=True,
            is_stop_requested=False,
            is_create_dir=True,
            is_root_locked=False,
        )
        == StateStatus.NO_FILES_FOUND_FOLDER_DELETED
    )

    assert (
        get_status(
            is_success=False,
            is_none_found=True,
            is_stop_requested=False,
            is_create_dir=True,
            is_root_locked=True,
        )
        == StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED
    )

    assert (
        get_status(
            is_success=False,
            is_none_found=False,
            is_stop_requested=True,
            is_create_dir=False,
            is_root_locked=False,
        )
        == StateStatus.USER_STOPPED
    )

    assert (
        get_status(
            is_success=False,
            is_none_found=False,
            is_stop_requested=False,
            is_create_dir=False,
            is_root_locked=True,
        )
        == StateStatus.ALL_FILES_SEARCHED
    )

    assert (
        get_status(
            is_success=False,
            is_none_found=False,
            is_stop_requested=False,
            is_create_dir=True,
            is_root_locked=False,
        )
        == StateStatus.UNDEFINED
    )

    assert (
        get_status(
            is_success=False,
            is_none_found=True,
            is_stop_requested=False,
            is_create_dir=False,
            is_root_locked=False,
        )
        == StateStatus.UNDEFINED
    )


def test_get_report() -> None:
    """Test get_report."""
    assert get_report(
        path="dest",
        size_str="1.00 KB",
        runtime_str="0:00:01",
        count=5,
        target_qty=10,
    ) == (
        "------------------------------------------------------------------------\n"
        "5/10 files transferred\n"
        "------------------------------------------------------------------------\n"
        "Destination:  dest\n"
        "Size:         1.00 KB\n"
        "Runtime:      0:00:01\n"
        "========================================================================\n"
    )
