"""Core services layer conftest.

Provides fixtures specific to unit testing of core domain services.
These fixtures are inherited from higher-level conftest files and supplement
them with core service-specific test utilities.

Fixture Hierarchy:
1. tests/conftest.py (global - all tests)
2. tests/unit/conftest.py (unit tests)
3. tests/unit/core/conftest.py (core services - this file)
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

import pytest

from roadmap.core.interfaces.parsers import IssueParserInterface
from roadmap.core.interfaces.persistence import PersistenceInterface
from roadmap.core.services.baseline.baseline_state_retriever import (
    BaselineStateRetriever,
)
from tests.fixtures.issue_factory import IssueFactory

# ============================================================================
# BaselineStateRetriever Fixtures
# ============================================================================


@pytest.fixture
def temp_issues_dir():
    """Temporary directory for issue files in baseline tests.

    Returns:
        Path to temporary directory cleaned up after test
    """
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


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
def baseline_retriever(temp_issues_dir, mock_persistence, mock_parser):
    """Create a BaselineStateRetriever with mock dependencies.

    Args:
        temp_issues_dir: Temporary directory fixture
        mock_persistence: Mock persistence interface
        mock_parser: Mock parser interface

    Returns:
        Configured BaselineStateRetriever instance
    """
    return BaselineStateRetriever(
        temp_issues_dir,
        mock_persistence,
        mock_parser,
    )


# ============================================================================
# Issue Factory Fixtures
# ============================================================================


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
