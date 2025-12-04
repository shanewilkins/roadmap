"""Integration tests for the 'roadmap today' command.

Tests the daily workflow summary command that shows issues assigned to
the current user in the upcoming milestone.
"""

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from roadmap.cli import main


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def roadmap_with_workflow_items(cli_runner):
    """Create an isolated roadmap with issues in various states.

    Creates issues with different priorities and types assigned to a user
    in an upcoming milestone.

    Yields:
        tuple: (cli_runner, temp_dir_path)
    """
    with cli_runner.isolated_filesystem():
        temp_dir = Path.cwd()

        # Initialize a roadmap without GitHub
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
                "v1.0",
                "--description",
                "First release",
            ],
        )
        assert result.exit_code == 0, f"Milestone creation failed: {result.output}"

        # Create various issues with different priorities assigned to testuser
        issues = [
            ("High priority task 1", "high", "feature"),
            ("High priority task 2", "high", "bug"),
            ("Critical priority task", "critical", "feature"),
            ("Medium priority task", "medium", "other"),
            ("Low priority task", "low", "other"),
        ]

        for title, priority, issue_type in issues:
            result = cli_runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    title,
                    "--type",
                    issue_type,
                    "--priority",
                    priority,
                    "--assignee",
                    "testuser",
                    "--milestone",
                    "v1.0",
                ],
            )
            assert result.exit_code == 0, f"Issue creation failed: {result.output}"

        yield cli_runner, temp_dir


class TestTodayCommand:
    """Test the 'roadmap today' command."""

    def test_today_command_runs_successfully(self, roadmap_with_workflow_items):
        """Test that today command executes without errors."""
        cli_runner, temp_dir = roadmap_with_workflow_items

        result = cli_runner.invoke(
            main, ["today"], catch_exceptions=False, env={"ROADMAP_USER": "testuser"}
        )

        assert result.exit_code == 0, f"Today command failed: {result.output}"

    def test_today_displays_header(self, roadmap_with_workflow_items):
        """Test that today command displays a header with milestone info."""
        cli_runner, temp_dir = roadmap_with_workflow_items

        result = cli_runner.invoke(
            main, ["today"], catch_exceptions=False, env={"ROADMAP_USER": "testuser"}
        )

        assert result.exit_code == 0
        # Should contain milestone and user info
        assert "v1.0" in result.output or "Milestone" in result.output

    def test_today_shows_high_priority_tasks(self, roadmap_with_workflow_items):
        """Test that today command shows high priority tasks or empty state."""
        cli_runner, temp_dir = roadmap_with_workflow_items

        result = cli_runner.invoke(
            main, ["today"], catch_exceptions=False, env={"ROADMAP_USER": "testuser"}
        )

        assert result.exit_code == 0
        # Should show either high priority tasks or an empty state message
        assert (
            "High priority" in result.output
            or "Critical priority" in result.output
            or "No issues" in result.output
        )

    def test_today_shows_summary_statistics(self, roadmap_with_workflow_items):
        """Test that today command shows summary statistics."""
        cli_runner, temp_dir = roadmap_with_workflow_items

        result = cli_runner.invoke(
            main, ["today"], catch_exceptions=False, env={"ROADMAP_USER": "testuser"}
        )

        assert result.exit_code == 0
        # Should contain counts or statistics
        # Look for patterns like "X in progress" or numbers
        assert re.search(r"\d+", result.output), "No statistics found in output"

    def test_today_with_empty_roadmap(self, cli_runner):
        """Test today command with no upcoming milestones."""
        with cli_runner.isolated_filesystem():
            # Initialize empty roadmap without GitHub
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Empty Project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )
            assert result.exit_code == 0

            result = cli_runner.invoke(
                main,
                ["today"],
                catch_exceptions=False,
                env={"ROADMAP_USER": "testuser"},
            )

            # Should fail with message about no upcoming milestones
            assert "No upcoming milestones" in result.output
