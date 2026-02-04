"""Test fixtures for health adapter tests."""

import pytest

from roadmap.infrastructure.coordination.core import RoadmapCore


@pytest.fixture
def core(tmp_path):
    """Create a RoadmapCore instance for testing."""
    instance = RoadmapCore(root_path=tmp_path)
    yield instance
    # Cleanup: close database connection
    try:
        if hasattr(instance, "db") and hasattr(instance.db, "close"):
            instance.db.close()
    except Exception:
        pass
