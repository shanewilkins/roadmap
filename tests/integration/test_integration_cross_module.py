"""
Integration tests for the roadmap CLI tool.

These tests verify end-to-end workflows and cross-module integration.
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.core.domain import Priority, Status
from roadmap.infrastructure.core import RoadmapCore

pytestmark = pytest.mark.filesystem


@pytest.fixture
def mock_github_client():
    """Mock GitHub client for integration operations."""
    with patch("roadmap.adapters.github.github.GitHubClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock successful API responses
        mock_client.test_connection.return_value = (True, "Connected successfully")
        mock_client.create_issue.return_value = {
            "number": 1,
            "html_url": "https://github.com/test/repo/issues/1",
        }
        mock_client.update_issue.return_value = {"number": 1}
        mock_client.create_milestone.return_value = {
            "number": 1,
            "html_url": "https://github.com/test/repo/milestones/1",
        }
        mock_client.get_issues.return_value = []
        mock_client.get_milestones.return_value = []

        yield mock_client


class TestCrossModuleIntegration:
    """Test integration between different modules."""

    def test_parser_core_integration(self, temp_workspace):
        """Test parser and core integration with real files."""
        runner = CliRunner()

        # Initialize and create data
        runner.invoke(
            main,
            [
                "init",
                "--non-interactive",
                "--skip-github",
                "--project-name",
                "test-project",
            ],
        )
        runner.invoke(main, ["issue", "create", "Test issue"])

        # Verify core can read what was created
        core = RoadmapCore()
        issues = core.issues.list()

        assert len(issues) == 1
        assert issues[0].title == "Test issue"

        # Verify files exist in the expected structure
        assert os.path.exists(".roadmap")
        assert os.path.exists(".roadmap/issues")
        # Use recursive glob to find issue files in subdirectories (backlog, milestone dirs, etc.)
        issue_files = list(Path(".roadmap/issues").glob("**/*.md"))
        assert len(issue_files) == 1

    def test_cli_core_parser_integration(self, temp_workspace):
        """Test full CLI -> Core -> Parser integration."""
        runner = CliRunner()

        # Create data through CLI
        runner.invoke(
            main,
            [
                "init",
                "--non-interactive",
                "--skip-github",
                "--project-name",
                "test-project",
            ],
        )
        result = runner.invoke(
            main, ["issue", "create", "CLI Issue", "--priority", "high"]
        )

        # Extract issue ID
        from tests.fixtures.click_testing import ClickTestHelper

        issue_id = ClickTestHelper.extract_issue_id(result.output)

        # Update through CLI
        assert issue_id is not None, "Could not find issue ID in output"
        runner.invoke(main, ["issue", "update", issue_id, "--status", "in-progress"])

        # Verify data through core
        core = RoadmapCore()
        core_issues = core.issues.list()

        assert len(core_issues) == 1
        core_issue = core_issues[0]
        assert core_issue.title == "CLI Issue"
        assert core_issue.priority == Priority.HIGH
        assert core_issue.status == Status.IN_PROGRESS

        # Verify the issue ID matches
        assert core_issue.id == issue_id
