"""Tests for the model."""

from fspachinko.domain.model import DiversityPolicy


def test_diversity_quota() -> None:
    """Test the DiversityQuota class."""
    quota = DiversityPolicy(root="/root", max_per_dir=2, unique_files_only=True)
    assert quota.root == "/root"
    assert quota.max_per_dir == 2
    assert quota.unique_files_only is True
    quota.update(parent="/root", path="/root/file1")
    assert quota.can_accept(parent="/root", path="/root/file1") is False
    assert quota.can_accept(parent="/root", path="/root/file2") is True
    quota.update(parent="/root", path="/root/file2")
    assert quota.can_accept(parent="/root", path="/root/file3") is False
    assert quota.is_root_locked is True
    quota.reset()
    assert len(quota.files) > 0
    assert len(quota.directories) == 0
    quota.unique_files_only = False
    quota.reset()
    assert len(quota.files) == 0
