"""Test helper functions."""

import pytest

from fspachinko.constants import StateStatus
from fspachinko.helpers import filesize_str, get_report, get_status


@pytest.mark.parametrize(
    ("nbytes", "expected"),
    [
        (500, "Size: 500.00 B"),
        (2048, "Size: 2.00 KB"),
        (5 * 1024**2, "Size: 5.00 MB"),
        (3 * 1024**3, "Size: 3.00 GB"),
    ],
)
def test_convert_byte_to_human_readable_size(nbytes: int, expected: str) -> None:
    """Test convert_byte_to_human_readable_size."""
    assert filesize_str(nbytes) == expected


@pytest.mark.parametrize(
    ("params", "expected_status"),
    [
        ((True, False, False, False), StateStatus.SUCCESS),
        ((False, True, False, False), StateStatus.NO_FILES_FOUND_FOLDER_DELETED),
        ((False, True, False, True), StateStatus.NO_FILES_FOUND_ALL_SEARCHED_FOLDER_DELETED),
        ((False, False, True, False), StateStatus.USER_STOPPED),
        ((False, False, False, True), StateStatus.ALL_FILES_SEARCHED),
        ((False, False, False, False), StateStatus.UNDEFINED),
    ],
)
def test_get_status(params: tuple[bool, ...], expected_status: str) -> None:
    """Test get_status."""
    success, empty_creation, stop_requested, root_locked = params
    status = get_status(
        success=success,
        empty_creation=empty_creation,
        stop_requested=stop_requested,
        root_locked=root_locked,
    )
    assert status == expected_status


def test_get_report() -> None:
    """Test get_report."""
    report = get_report("/path/to/destination", 5 * 1024**2, 3, 10)
    expected_report = (
        "------------------------------------------------------------------------\n"
        "3/10 (30.00%) files transferred\n"
        "------------------------------------------------------------------------\n"
        "Destination: /path/to/destination\n"
        "Size: 5.00 MB\n"
        "========================================================================\n"
    )
    assert report == expected_report
