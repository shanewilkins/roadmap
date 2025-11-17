"""Shared test fixtures and configuration for CLI tests."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from roadmap.cli import main
from roadmap.models import Priority, Status


@pytest.fixture(autouse=True)
def reset_cli_state():
    """Reset CLI state between tests to prevent pollution."""
    # Clear any cached Click contexts and CLI state
    import os
    import sys

    # Store original environment
    original_cwd = os.getcwd()
    original_env = os.environ.copy()

    # Clear Click-related caches if they exist
    if hasattr(main, 'make_context'):
        try:
            ctx = main.make_context('main', [])
            ctx.reset()
        except:
            pass

    # Clear any module-level state
    if hasattr(sys.modules.get('roadmap.cli'), '_cached_core'):
        delattr(sys.modules['roadmap.cli'], '_cached_core')

    yield

    # Restore original state
    os.chdir(original_cwd)
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def cli_runner():
    """Create an isolated CLI runner for testing."""
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(original_cwd)


@pytest.fixture
def cli_isolated_fs():
    """CLI runner with isolated filesystem."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        yield runner


@pytest.fixture
def initialized_roadmap(temp_dir):
    """Provide a temporary directory with an initialized roadmap."""
    from roadmap.core import RoadmapCore

    # Initialize the roadmap
    manager = RoadmapCore()
    manager.initialize()  # The correct method name

    yield temp_dir


@pytest.fixture
def mock_github_client():
    """Mock GitHub client for testing sync operations."""
    with patch('roadmap.github_client.GitHubClient') as mock:
        # Mock successful authentication
        mock.return_value.test_connection.return_value = True
        mock.return_value.get_issues.return_value = []
        mock.return_value.get_milestones.return_value = []
        mock.return_value.create_issue.return_value = {'number': 1, 'html_url': 'https://github.com/test/test/issues/1'}
        mock.return_value.create_milestone.return_value = {'number': 1, 'html_url': 'https://github.com/test/test/milestones/1'}
        yield mock


@pytest.fixture
def sample_issue():
    """Provide a sample issue for testing."""
    from roadmap.models import Issue
    return Issue(
        id="issue-1",
        title="Sample Issue",
        description="A sample issue for testing",
        status=Status.OPEN,
        priority=Priority.MEDIUM,
        assignee="test-user",
        estimated_hours=5.0,
        tags=["feature", "backend"]
    )


@pytest.fixture
def sample_milestone():
    """Provide a sample milestone for testing."""
    from roadmap.models import Milestone
    return Milestone(
        id="milestone-1",
        title="Sample Milestone",
        description="A sample milestone for testing",
        due_date="2024-12-31"
    )
