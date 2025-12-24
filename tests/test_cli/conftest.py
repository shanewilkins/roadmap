"""Test configuration and fixtures for test_cli tests.

Provides access to TestDataFactory and common fixtures for all CLI tests.
"""

import pytest

from tests.unit.domain.test_data_factory import TestDataFactory


@pytest.fixture
def test_factory():
    """Provide access to TestDataFactory for all tests.

    Returns:
        TestDataFactory class with all factory methods
    """
    return TestDataFactory


@pytest.fixture
def mock_git():
    """Create a basic mock git integration."""
    return TestDataFactory.create_mock_core()


@pytest.fixture
def mock_core():
    """Create a basic mock RoadmapCore."""
    return TestDataFactory.create_mock_core()


@pytest.fixture
def mock_config():
    """Create a basic mock configuration."""
    return TestDataFactory.create_mock_config()


@pytest.fixture
def mock_issue():
    """Create a basic mock issue."""
    return TestDataFactory.create_mock_issue()


@pytest.fixture
def mock_milestone():
    """Create a basic mock milestone."""
    return TestDataFactory.create_mock_milestone()
