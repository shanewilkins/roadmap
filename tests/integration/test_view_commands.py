"""Integration tests for view commands (issue view, milestone view, project view).

Tests the detailed view commands that display formatted information about individual items.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from roadmap.cli import main


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def roadmap_with_data(cli_runner):
    """Create an isolated roadmap with issues, milestones, and projects.

    Yields:
        tuple: (cli_runner, temp_dir_path, data_dict)
    """
    with cli_runner.isolated_filesystem():
        temp_dir = Path.cwd()

        # Initialize a roadmap
        result = cli_runner.invoke(
            main,
            [
                "init",
                "--project-name",
                "Test Project",
                "--non-interactive",
                "--skip-github",
            ],
        )
        assert result.exit_code == 0, f"Init failed: {result.output}"

        # Create a milestone
        result = cli_runner.invoke(
            main,
            [
                "milestone",
                "create",
                "v1.0.0",
                "--description",
                "First release",
                "--due-date",
                (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            ],
        )
        assert result.exit_code == 0, f"Milestone creation failed: {result.output}"

        # Create an issue
        result = cli_runner.invoke(
            main,
            [
                "issue",
                "create",
                "Test issue for viewing",
                "--type",
                "feature",
                "--priority",
                "high",
                "--milestone",
                "v1.0.0",
            ],
        )
        assert result.exit_code == 0, f"Issue creation failed: {result.output}"

        # Extract issue ID from output
        match = re.search(r"ID:\s+([a-f0-9-]+)", result.output)
        assert match, f"Could not find issue ID in output: {result.output}"
        issue_id = match.group(1)

        # Create a project
        result = cli_runner.invoke(
            main,
            [
                "project",
                "create",
                "test-project",
                "--description",
                "A test project",
            ],
        )
        assert result.exit_code == 0, f"Project creation failed: {result.output}"

        yield (
            cli_runner,
            temp_dir,
            {
                "issue_id": issue_id,
                "milestone_name": "v1.0.0",
                "project_id": "test-project",
            },
        )


class TestIssueViewCommand:
    """Test the 'roadmap issue view' command."""

    def test_issue_view_displays_basic_info(self, roadmap_with_data):
        """Test that issue view displays basic issue information."""
        cli_runner, temp_dir, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["issue", "view", data["issue_id"]], catch_exceptions=False
        )

        assert result.exit_code == 0, f"Issue view failed: {result.output}"
        assert "Test issue for viewing" in result.output
        assert data["issue_id"] in result.output
        assert "high" in result.output.lower() or "HIGH" in result.output

    def test_issue_view_displays_milestone(self, roadmap_with_data):
        """Test that issue view displays associated milestone."""
        cli_runner, temp_dir, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["issue", "view", data["issue_id"]], catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "v1.0.0" in result.output

    def test_issue_view_displays_type(self, roadmap_with_data):
        """Test that issue view displays the type."""
        cli_runner, temp_dir, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["issue", "view", data["issue_id"]], catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "feature" in result.output.lower() or "FEATURE" in result.output

    def test_issue_view_nonexistent_issue(self, roadmap_with_data):
        """Test viewing a non-existent issue."""
        cli_runner, temp_dir, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["issue", "view", "00000000-0000-0000-0000-000000000000"]
        )

        assert result.exit_code != 0
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
        )


class TestMilestoneViewCommand:
    """Test the 'roadmap milestone view' command."""

    def test_milestone_view_displays_basic_info(self, roadmap_with_data):
        """Test that milestone view displays basic milestone information."""
        cli_runner, temp_dir, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["milestone", "view", data["milestone_name"]], catch_exceptions=False
        )

        assert result.exit_code == 0, f"Milestone view failed: {result.output}"
        assert "v1.0.0" in result.output
        assert "First release" in result.output

    def test_milestone_view_displays_progress(self, roadmap_with_data):
        """Test that milestone view displays progress information."""
        cli_runner, temp_dir, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["milestone", "view", data["milestone_name"]], catch_exceptions=False
        )

        assert result.exit_code == 0
        # Should show progress (0/1 or similar since we created 1 issue)
        assert re.search(r"\d+/\d+", result.output), "Progress count not found"

    def test_milestone_view_displays_issues(self, roadmap_with_data):
        """Test that milestone view displays associated issues."""
        cli_runner, temp_dir, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["milestone", "view", data["milestone_name"]], catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Test issue for viewing" in result.output

    def test_milestone_view_nonexistent_milestone(self, roadmap_with_data):
        """Test viewing a non-existent milestone."""
        cli_runner, temp_dir, data = roadmap_with_data

        result = cli_runner.invoke(main, ["milestone", "view", "v99.99.99"])

        assert result.exit_code != 0
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
        )


class TestProjectViewCommand:
    """Test the 'roadmap project view' command."""

    def test_project_view_displays_basic_info(self, roadmap_with_data):
        """Test that project view displays basic project information."""
        cli_runner, temp_dir, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["project", "view", data["project_id"]], catch_exceptions=False
        )

        assert result.exit_code == 0, f"Project view failed: {result.output}"
        assert "Test Project" in result.output
        assert "test-project" in result.output

    def test_project_view_displays_description(self, roadmap_with_data):
        """Test that project view displays the description."""
        cli_runner, temp_dir, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["project", "view", data["project_id"]], catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "A test project" in result.output

    def test_project_view_nonexistent_project(self, roadmap_with_data):
        """Test viewing a non-existent project."""
        cli_runner, temp_dir, data = roadmap_with_data

        result = cli_runner.invoke(main, ["project", "view", "nonexistent-project"])

        assert result.exit_code != 0
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
        )
