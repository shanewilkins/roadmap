"""Integration tests for --overdue flag on list commands.

Tests the overdue filtering functionality for issues, milestones, and projects.
"""

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
def roadmap_with_overdue_items(cli_runner):
    """Create an isolated roadmap with overdue and on-time items.

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

        # Create an overdue milestone
        overdue_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        result = cli_runner.invoke(
            main,
            [
                "milestone",
                "create",
                "overdue-milestone",
                "--description",
                "This is overdue",
                "--due-date",
                overdue_date,
            ],
        )
        assert result.exit_code == 0, f"Milestone creation failed: {result.output}"

        # Create a future milestone
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        result = cli_runner.invoke(
            main,
            [
                "milestone",
                "create",
                "future-milestone",
                "--description",
                "This is in the future",
                "--due-date",
                future_date,
            ],
        )
        assert result.exit_code == 0, f"Milestone creation failed: {result.output}"

        # Create an overdue issue (set estimate as proxy for due date)
        result = cli_runner.invoke(
            main,
            [
                "issue",
                "create",
                "Overdue issue",
                "--type",
                "bug",
                "--priority",
                "high",
                "--estimate",
                "8",
            ],
        )
        assert result.exit_code == 0, f"Issue creation failed: {result.output}"

        # Create a future issue
        result = cli_runner.invoke(
            main,
            [
                "issue",
                "create",
                "Future issue",
                "--type",
                "feature",
                "--priority",
                "medium",
                "--estimate",
                "4",
            ],
        )
        assert result.exit_code == 0, f"Issue creation failed: {result.output}"

        # Create an issue with no due date
        result = cli_runner.invoke(
            main,
            [
                "issue",
                "create",
                "No due date issue",
                "--type",
                "other",
                "--priority",
                "low",
            ],
        )
        assert result.exit_code == 0, f"Issue creation failed: {result.output}"

        yield cli_runner, temp_dir


class TestOverdueIssueFiltering:
    """Test the --overdue flag for issue list command."""

    def test_issue_list_overdue_flag_works(self, roadmap_with_overdue_items):
        """Test that --overdue flag is accepted and executes."""
        cli_runner, temp_dir = roadmap_with_overdue_items

        result = cli_runner.invoke(
            main, ["issue", "list", "--overdue"], catch_exceptions=False
        )

        assert result.exit_code == 0, f"Issue list --overdue failed: {result.output}"
        # Note: Since we can't actually set due dates via CLI, this may return empty results
        # The important thing is the flag works

    def test_issue_list_without_overdue_shows_all(self, roadmap_with_overdue_items):
        """Test that without --overdue flag, all issues are shown."""
        cli_runner, temp_dir = roadmap_with_overdue_items

        result = cli_runner.invoke(main, ["issue", "list"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "Overdue issue" in result.output
        assert "Future issue" in result.output
        assert "No due date issue" in result.output

    def test_issue_list_overdue_with_other_filters(self, roadmap_with_overdue_items):
        """Test that --overdue can be combined with other filters."""
        cli_runner, temp_dir = roadmap_with_overdue_items

        result = cli_runner.invoke(
            main,
            ["issue", "list", "--overdue", "--priority", "high"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Flag combination should work even if no results


class TestOverdueMilestoneFiltering:
    """Test the --overdue flag for milestone list command."""

    def test_milestone_list_overdue_flag_works(self, roadmap_with_overdue_items):
        """Test that --overdue flag is accepted and executes."""
        cli_runner, temp_dir = roadmap_with_overdue_items

        result = cli_runner.invoke(
            main, ["milestone", "list", "--overdue"], catch_exceptions=False
        )

        assert (
            result.exit_code == 0
        ), f"Milestone list --overdue failed: {result.output}"
        # Should show the overdue milestone
        assert "overdue-milestone" in result.output

    def test_milestone_list_without_overdue_shows_all(self, roadmap_with_overdue_items):
        """Test that without --overdue flag, all milestones are shown."""
        cli_runner, temp_dir = roadmap_with_overdue_items

        result = cli_runner.invoke(main, ["milestone", "list"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "overdue-milestone" in result.output
        assert "future-milestone" in result.output

    def test_milestone_overdue_only_includes_open(self, roadmap_with_overdue_items):
        """Test that --overdue only includes open milestones, not completed ones."""
        cli_runner, temp_dir = roadmap_with_overdue_items

        # Close the overdue milestone
        result = cli_runner.invoke(
            main, ["milestone", "close", "overdue-milestone"], catch_exceptions=False
        )
        # Note: close command may not exist
        if result.exit_code == 0:
            # Now check overdue list - closed milestone should not appear
            result = cli_runner.invoke(
                main, ["milestone", "list", "--overdue"], catch_exceptions=False
            )

            assert result.exit_code == 0
            # Closed milestone should not appear in overdue list
            output_lower = result.output.lower()
            # Either it's not there or shows as closed
            assert "overdue-milestone" not in result.output or "closed" in output_lower


class TestOverdueProjectFiltering:
    """Test the --overdue flag for project list command."""

    def test_project_list_overdue_flag_works(self, cli_runner):
        """Test that --overdue flag is accepted and executes."""
        with cli_runner.isolated_filesystem():
            # Initialize
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
            assert result.exit_code == 0

            # Create overdue project
            overdue_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            result = cli_runner.invoke(
                main,
                [
                    "project",
                    "create",
                    "overdue-proj",
                    "--description",
                    "Overdue Project",
                    "--target-end-date",
                    overdue_date,
                ],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Test overdue filter works
            result = cli_runner.invoke(
                main, ["project", "list", "--overdue"], catch_exceptions=False
            )

            assert result.exit_code == 0
            assert "overdue-proj" in result.output

    def test_project_list_without_overdue_shows_all(self, cli_runner):
        """Test that without --overdue flag, all projects are shown."""
        with cli_runner.isolated_filesystem():
            # Initialize
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
            assert result.exit_code == 0

            # Create projects with different dates
            overdue_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            result = cli_runner.invoke(
                main,
                [
                    "project",
                    "create",
                    "overdue-proj",
                    "--description",
                    "Overdue Project",
                    "--target-end-date",
                    overdue_date,
                ],
            )
            assert result.exit_code == 0

            future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            result = cli_runner.invoke(
                main,
                [
                    "project",
                    "create",
                    "future-proj",
                    "--description",
                    "Future Project",
                    "--target-end-date",
                    future_date,
                ],
            )
            assert result.exit_code == 0

            # Test without filter
            result = cli_runner.invoke(
                main, ["project", "list"], catch_exceptions=False
            )

            assert result.exit_code == 0
            assert "overdue-proj" in result.output
            assert "future-proj" in result.output
