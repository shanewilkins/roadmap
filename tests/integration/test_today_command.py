"""Integration tests for the 'roadmap today' command.

Tests the daily workflow summary command that shows in-progress, overdue,
blocked, upcoming, and completed tasks.
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

    Creates issues with different priorities and types.

    Yields:
        tuple: (cli_runner, temp_dir_path)
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

        # Create various issues with different priorities
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
                ],
            )
            assert result.exit_code == 0, f"Issue creation failed: {result.output}"

        yield cli_runner, temp_dir


class TestTodayCommand:
    """Test the 'roadmap today' command."""

    def test_today_command_runs_successfully(self, roadmap_with_workflow_items):
        """Test that today command executes without errors."""
        cli_runner, temp_dir = roadmap_with_workflow_items

        result = cli_runner.invoke(main, ["today"], catch_exceptions=False)

        assert result.exit_code == 0, f"Today command failed: {result.output}"

    def test_today_displays_header(self, roadmap_with_workflow_items):
        """Test that today command displays a header with current date."""
        cli_runner, temp_dir = roadmap_with_workflow_items

        result = cli_runner.invoke(main, ["today"], catch_exceptions=False)

        assert result.exit_code == 0
        # Should contain date-related text
        assert (
            "Daily" in result.output
            or "Today" in result.output
            or "Summary" in result.output
        )

    def test_today_shows_high_priority_tasks(self, roadmap_with_workflow_items):
        """Test that today command shows high priority tasks."""
        cli_runner, temp_dir = roadmap_with_workflow_items

        result = cli_runner.invoke(main, ["today"], catch_exceptions=False)

        assert result.exit_code == 0
        # Should show at least some high priority tasks
        assert "High priority" in result.output or "Critical priority" in result.output

    def test_today_shows_summary_statistics(self, roadmap_with_workflow_items):
        """Test that today command shows summary statistics."""
        cli_runner, temp_dir = roadmap_with_workflow_items

        result = cli_runner.invoke(main, ["today"], catch_exceptions=False)

        assert result.exit_code == 0
        # Should contain counts or statistics
        # Look for patterns like "X in progress" or numbers
        assert re.search(r"\d+", result.output), "No statistics found in output"

    def test_today_with_empty_roadmap(self, cli_runner):
        """Test today command with no issues."""
        with cli_runner.isolated_filesystem():
            # Initialize empty roadmap
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

            result = cli_runner.invoke(main, ["today"], catch_exceptions=False)

            assert result.exit_code == 0
            # Should handle empty case gracefully
            # May show "No issues" or "0 in progress" or similar
            output_lower = result.output.lower()
            assert (
                "0" in result.output
                or "no" in output_lower
                or "empty" in output_lower
                or "nothing" in output_lower
            )
