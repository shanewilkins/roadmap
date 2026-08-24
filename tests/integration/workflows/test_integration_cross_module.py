"""Integration tests for the roadmap CLI tool.

These tests verify end-to-end workflows and cross-module integration.
"""

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from roadmap.bootstrap import cli as main
from roadmap.core.domain import Priority, Status
from roadmap.infrastructure.coordination.core import RoadmapCore

pytestmark = pytest.mark.filesystem


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
                "--project-name",
                "test-project",
            ],
        )
        runner.invoke(main, ["issue", "create", "--title", "Test issue"])

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
                "--project-name",
                "test-project",
            ],
        )
        result = runner.invoke(
            main, ["issue", "create", "--title", "CLI Issue", "--priority", "high"]
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
