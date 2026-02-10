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

from roadmap.core.interfaces.parsers import IssueParserInterface
from roadmap.core.interfaces.persistence import PersistenceInterface
from tests.fixtures.issue_factory import IssueFactory
from tests.unit.domain.test_data_factory_generation import TestDataFactory

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


@pytest.fixture
def issue_factory():
    """Provide access to IssueFactory for creating test issues.

    Returns:
        IssueFactory class with static factory methods
    """
    return IssueFactory


# ============================================================================
# Persistence and Parser Mocks
# ============================================================================


@pytest.fixture
def mock_persistence():
    """Shared mock for PersistenceInterface.

    Returns:
        MagicMock with PersistenceInterface spec
    """
    return MagicMock(spec=PersistenceInterface)


@pytest.fixture
def mock_parser():
    """Shared mock for IssueParserInterface.

    Returns:
        MagicMock with IssueParserInterface spec
    """
    return MagicMock(spec=IssueParserInterface)


@pytest.fixture
def assert_not_called():
    """Helper to assert mock was not called.

    Returns:
        Function that validates mock was not called
    """

    def _assert(mock_obj):
        assert mock_obj.call_count == 0, (
            f"Expected mock not to be called, but was called {mock_obj.call_count} times"
        )
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


@pytest.fixture
def unit_roadmap_core(tmp_path):
    """Create a RoadmapCore instance for unit testing in isolation.

    Creates RoadmapCore in a temporary directory without full initialization
    for unit test scenarios that need a core instance but not full setup.

    Args:
        tmp_path: pytest temporary directory

    Returns:
        RoadmapCore instance with basic setup
    """
    import os

    from roadmap.infrastructure.coordination.core import RoadmapCore

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        core = RoadmapCore()
        # Note: Not calling initialize() - for unit tests that need bare instance
        yield core
    finally:
        os.chdir(original_cwd)
