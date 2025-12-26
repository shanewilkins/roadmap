"""Unit test configuration and fixtures.

This conftest provides fixtures specific to unit testing, organizing
fixtures by scope and test context. Fixtures are inherited from the
global conftest and supplemented with unit-specific ones here.

Fixture Organization (Unit Level):
- Mock factories and objects for unit isolation
- Domain layer service mocks
- Presentation layer CLI test helpers
- Adapter-specific fixtures

Fixture Hierarchy:
1. tests/conftest.py (global - all tests)
2. tests/unit/conftest.py (unit tests - this file)
3. tests/unit/domain/conftest.py (domain layer specifics)
4. tests/unit/presentation/conftest.py (CLI layer specifics)
5. tests/unit/adapters/cli/health/conftest.py (health adapter specifics)
"""

from unittest.mock import MagicMock

import pytest

from tests.unit.domain.test_data_factory import TestDataFactory

# ============================================================================
# Core Object Factories for Unit Tests
# ============================================================================


@pytest.fixture
def factory():
    """Provide access to TestDataFactory for creating test data.

    Returns:
        TestDataFactory class with factory methods
    """
    return TestDataFactory


# ============================================================================
# Unit Test Assertions and Helpers
# ============================================================================


@pytest.fixture
def assert_mock_called_with_args():
    """Helper to assert mock was called with specific arguments.

    Returns:
        Function that validates mock call arguments
    """

    def _assert(mock_obj, expected_args=None, expected_kwargs=None):
        expected_args = expected_args or ()
        expected_kwargs = expected_kwargs or {}
        mock_obj.assert_called_once_with(*expected_args, **expected_kwargs)
        return True

    return _assert


@pytest.fixture
def assert_not_called():
    """Helper to assert mock was not called.

    Returns:
        Function that validates mock was not called
    """

    def _assert(mock_obj):
        assert (
            mock_obj.call_count == 0
        ), f"Expected mock not to be called, but was called {mock_obj.call_count} times"
        return True

    return _assert


# ============================================================================
# Unit Test Isolation Utilities
# ============================================================================


@pytest.fixture
def unit_test_config():
    """Provide unit test configuration settings.

    Returns:
        Dictionary of unit test configuration
    """
    return {
        "use_real_fs": False,
        "use_real_git": False,
        "use_real_github": False,
        "use_mocks": True,
        "isolation_level": "unit",
    }


@pytest.fixture
def mock_any():
    """Provide a mock that matches any value for assertion testing.

    Returns:
        MagicMock configured to match any value
    """
    return MagicMock()
