"""Core services layer conftest.

Provides fixtures specific to unit testing of core domain services.
These fixtures are inherited from higher-level conftest files and supplement
them with core service-specific test utilities.

Fixture Hierarchy:
1. tests/conftest.py (global - all tests)
2. tests/unit/conftest.py (unit tests)
3. tests/unit/core/conftest.py (core services - this file)
"""

import pytest

from tests.fixtures.issue_factory import IssueFactory


@pytest.fixture
def issue_factory():
    """Provide access to IssueFactory for creating test issues.

    Returns:
        IssueFactory class with static factory methods
    """
    return IssueFactory


@pytest.fixture
def sample_issue():
    """Create a sample issue for testing.

    Returns:
        Issue instance with typical test values
    """
    return IssueFactory.create(
        id="test-1",
        title="Test Issue",
        content="Test content",
    )


@pytest.fixture
def sample_issues():
    """Create multiple sample issues for batch testing.

    Returns:
        List of 5 Issue instances
    """
    return IssueFactory.create_batch(count=5)
