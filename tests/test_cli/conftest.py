"""Test configuration and fixtures for test_cli tests.

Provides access to TestDataFactory and common fixtures for all CLI tests.

Fixtures are imported from tests.fixtures.mocks to ensure centralization
and consistency across all test files.
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
