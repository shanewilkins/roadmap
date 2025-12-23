"""Shared test fixtures and configuration for presentation (CLI) layer tests."""

import os
import tempfile
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main


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
    if hasattr(main, "make_context"):
        try:
            main.make_context("main", [])
            # Context reset not available, skip
            pass
        except Exception:  # noqa: BLE001
            pass

    # Clear any module-level state
    if hasattr(sys.modules.get("roadmap.cli"), "_cached_core"):
        delattr(sys.modules["roadmap.cli"], "_cached_core")

    yield

    # Restore original state
    os.chdir(original_cwd)
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def cli_runner():
    """Create an isolated CLI runner for testing."""
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
def initialized_roadmap():
    """Provide a CliRunner with an initialized roadmap in isolated filesystem."""
    from roadmap.infrastructure.core import RoadmapCore

    runner = CliRunner()

    with runner.isolated_filesystem():
        # Initialize the roadmap
        manager = RoadmapCore()
        manager.initialize()

        yield runner


@pytest.fixture
def mock_github_client():
    """Mock GitHub client for testing sync operations."""
    with patch("roadmap.adapters.github.github.GitHubClient") as mock:
        # Mock successful authentication
        mock.return_value.test_connection.return_value = True
        mock.return_value.get_issues.return_value = []
        mock.return_value.get_milestones.return_value = []
        mock.return_value.create_issue.return_value = {
            "number": 1,
            "html_url": "https://github.com/test/test/issues/1",
        }
        mock.return_value.create_milestone.return_value = {
            "number": 1,
            "html_url": "https://github.com/test/test/milestones/1",
        }
        yield mock
