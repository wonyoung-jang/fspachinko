"""Test helper functions."""

from fspachinko.constants import StateStatus
from fspachinko.helpers import convert_byte_to_human_readable_size, get_report, get_status


def test_convert_byte_to_human_readable_size() -> None:
    """Test convert_byte_to_human_readable_size."""
    assert convert_byte_to_human_readable_size(500) == "500 B"
    assert convert_byte_to_human_readable_size(2048) == "2.00 KB"
    assert convert_byte_to_human_readable_size(5 * 1024**2) == "5.00 MB"
    assert convert_byte_to_human_readable_size(3 * 1024**3) == "3.00 GB"


def test_get_status() -> None:
    """Test get_status."""
    assert (
        get_status(
            is_success=True,
            is_none_found_and_create_dir=False,
            is_stop_requested=False,
            is_root_locked=False,
        )
        == StateStatus.SUCCESS
    )

    assert (
        get_status(
            is_success=False,
            is_none_found_and_create_dir=True,
            is_stop_requested=False,
            is_root_locked=False,
        )
        == StateStatus.NO_FILES_FOUND_FOLDER_DELETED
    )

    assert (
        get_status(
            is_success=False,
            is_none_found_and_create_dir=True,
            is_stop_requested=False,
            is_root_locked=True,
        )
        == StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED
    )

    assert (
        get_status(
            is_success=False,
            is_none_found_and_create_dir=False,
            is_stop_requested=True,
            is_root_locked=False,
        )
        == StateStatus.USER_STOPPED
    )

    assert (
        get_status(
            is_success=False,
            is_none_found_and_create_dir=False,
            is_stop_requested=False,
            is_root_locked=True,
        )
        == StateStatus.ALL_FILES_SEARCHED
    )

    assert (
        get_status(
            is_success=False,
            is_none_found_and_create_dir=False,
            is_stop_requested=False,
            is_root_locked=False,
        )
        == StateStatus.UNDEFINED
    )


def test_get_report() -> None:
    """Test get_report."""
    report = get_report("/path/to/destination", 5 * 1024**2, 3, 10)
    expected_report = (
        "------------------------------------------------------------------------\n"
        "3/10 files transferred\n"
        "------------------------------------------------------------------------\n"
        "Destination:  /path/to/destination\n"
        "Size:         5.00 MB\n"
        "========================================================================\n"
    )
    assert report == expected_report
