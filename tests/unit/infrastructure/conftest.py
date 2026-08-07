"""Infrastructure layer test fixtures."""

import pytest

from tests.unit.domain.test_data_factory_generation import TestDataFactory


@pytest.fixture
def mock_core(tmp_path):
    """Create mock RoadmapCore with temporary filesystem.

    This fixture provides a properly initialized mock RoadmapCore
    for infrastructure layer tests, with real filesystem support
    for integration-like tests.

    Args:
        tmp_path: pytest temporary directory fixture

    Returns:
        Mock RoadmapCore instance with temp roadmap directory
    """
    core = TestDataFactory.create_mock_core(is_initialized=True)
    core.roadmap_dir = tmp_path / ".roadmap"
    core.roadmap_dir.mkdir(exist_ok=True)
    return core
