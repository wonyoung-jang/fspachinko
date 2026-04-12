"""Tests for the model."""

from fspachinko.domain.model import DiversityQuota


def test_diversity_quota() -> None:
    """Test the DiversityQuota class."""
    quota = DiversityQuota(root="/root", max_per_dir=2)
    assert quota.root == "/root"
    assert quota.max_per_dir == 2
    quota.update(parent="/root")
    assert quota.can_accept(parent="/root") is True
    quota.update(parent="/root")
    assert quota.can_accept(parent="/root") is False
    assert quota.is_root_locked is True
    quota.reset()
    assert len(quota.directories) == 0
    quota.reset()
