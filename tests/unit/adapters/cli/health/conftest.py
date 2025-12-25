"""Test fixtures for health adapter tests."""

import pytest

from roadmap.infrastructure.core import RoadmapCore


@pytest.fixture
def core(tmp_path):
    """Create a RoadmapCore instance for testing."""
    return RoadmapCore(root_path=tmp_path)
