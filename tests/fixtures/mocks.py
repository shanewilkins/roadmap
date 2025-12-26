"""Mock fixtures for core objects and data.

Provides standardized mock objects for RoadmapCore, configuration, issues,
milestones, and other core domain objects.

This module centralizes all mock fixtures to avoid duplication across test files.
Tests should import these fixtures from here rather than defining their own.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from tests.unit.domain.test_data_factory import TestDataFactory


@pytest.fixture(scope="function")
def mock_core():
    """Create standardized mock RoadmapCore instance.

    This centralizes the mock_core fixture used across multiple test files.
    Individual tests can override specific behavior as needed.

    Returns:
        Mock RoadmapCore instance
    """
    return TestDataFactory.create_mock_core()


@pytest.fixture(scope="function")
def mock_core_initialized():
    """Create initialized mock RoadmapCore instance.

    Use this when you need a core that is already initialized.

    Returns:
        Initialized Mock RoadmapCore instance
    """
    return TestDataFactory.create_mock_core(is_initialized=True)


@pytest.fixture(scope="function")
def mock_core_with_github():
    """Create mock RoadmapCore with GitHub integration.

    Use this when testing GitHub-related operations.

    Returns:
        Mock RoadmapCore with GitHub service
    """
    return TestDataFactory.create_mock_core(
        is_initialized=True, github_service=MagicMock()
    )


@pytest.fixture(scope="function")
def mock_core_simple():
    """Create simple MagicMock core for basic tests.

    Use this when TestDataFactory.create_mock_core() is overkill.
    Useful for CLI tests that just need a mock object.

    Returns:
        Simple MagicMock instance
    """
    return MagicMock()


@pytest.fixture(scope="function")
def mock_config():
    """Create standardized mock RoadmapConfig instance.

    Returns:
        Mock RoadmapConfig instance
    """
    return TestDataFactory.create_mock_config()


@pytest.fixture(scope="function")
def mock_issue():
    """Create standardized mock Issue instance.

    Returns:
        Mock Issue instance
    """
    return TestDataFactory.create_mock_issue()


@pytest.fixture(scope="function")
def mock_milestone():
    """Create standardized mock Milestone instance.

    Returns:
        Mock Milestone instance
    """
    return TestDataFactory.create_mock_milestone()


@pytest.fixture
def lightweight_mock_core():
    """Create lightweight mock core for performance-critical tests.

    This provides minimal mocking for tests that don't need full core functionality.
    Suitable for unit tests that only need basic initialization check.

    Returns:
        Lightweight Mock RoadmapCore instance
    """
    core = Mock()
    core.is_initialized.return_value = True
    core.get_issues.return_value = []
    return core


@pytest.fixture
def fast_mock_core():
    """Create ultra-lightweight mock core with minimal setup.

    Even faster than lightweight_mock_core, useful for performance-critical paths.

    Returns:
        Ultra-lightweight Mock RoadmapCore instance
    """
    core = Mock()
    core.is_initialized.return_value = True
    core.workspace_root = Path("/tmp/fast_test")
    core.get_issues.return_value = []
    core.get_milestones.return_value = []
    return core


@pytest.fixture
def cli_test_data():
    """Create CLI test data factory function.

    Returns:
        Factory function for creating CLI test data
    """
    return TestDataFactory.create_cli_test_data


@pytest.fixture
def mock_console():
    """Create mock Rich console for output testing.

    Use this when testing commands that use Rich for output.
    Allows verification of console calls without actual output.

    Returns:
        Mock console instance
    """
    return MagicMock()
