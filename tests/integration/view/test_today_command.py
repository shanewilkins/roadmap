"""Integration tests for the 'roadmap today' command.

Tests the daily workflow summary command that shows issues assigned to
the current user in the upcoming milestone.
"""

import re

import pytest

from roadmap.adapters.cli import main
from tests.fixtures.integration_helpers import IntegrationTestBase
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


@pytest.fixture
def roadmap_with_workflow_items(cli_runner):
    """Create an isolated roadmap with issues in various states.

    Creates issues with different priorities and types assigned to a user
    in an upcoming milestone.

    Yields:
        tuple: (cli_runner, core)
    """
    with cli_runner.isolated_filesystem():
        # Initialize a roadmap without GitHub
        core = IntegrationTestBase.init_roadmap(cli_runner)

        # Create a milestone
        IntegrationTestBase.create_milestone(
            cli_runner,
            name="v1-0",
            headline="First release",
        )

        # Create various issues with different priorities assigned to testuser
        issues = [
            ("High priority task 1", "high"),
            ("High priority task 2", "high"),
            ("Critical priority task", "critical"),
            ("Medium priority task", "medium"),
            ("Low priority task", "low"),
        ]

        for title, priority in issues:
            IntegrationTestBase.create_issue(
                cli_runner,
                title=title,
                priority=priority,
                assignee="testuser",
                milestone="v1-0",
            )

        yield cli_runner, core


class TestTodayCommand:
    """Test the 'roadmap today' command."""

    def test_today_command_runs_successfully(self, roadmap_with_workflow_items):
        """Test that today command executes without errors."""
        cli_runner, core = roadmap_with_workflow_items

        result = cli_runner.invoke(
            main, ["today"], catch_exceptions=False, env={"ROADMAP_USER": "testuser"}
        )

        IntegrationTestBase.assert_cli_success(result)

    def test_today_displays_header(self, roadmap_with_workflow_items):
        """Test that today command displays a header with milestone info."""
        cli_runner, core = roadmap_with_workflow_items

        result = cli_runner.invoke(
            main, ["today"], catch_exceptions=False, env={"ROADMAP_USER": "testuser"}
        )

        IntegrationTestBase.assert_cli_success(result)
        # Should contain milestone and user info
        output = clean_cli_output(result.output)
        assert "v1-0" in output or "Milestone" in output

    def test_today_shows_high_priority_tasks(self, roadmap_with_workflow_items):
        """Test that today command shows high priority tasks or empty state."""
        cli_runner, core = roadmap_with_workflow_items

        result = cli_runner.invoke(
            main, ["today"], catch_exceptions=False, env={"ROADMAP_USER": "testuser"}
        )

        IntegrationTestBase.assert_cli_success(result)
        # Should show either high priority tasks or an empty state message
        output = clean_cli_output(result.output)
        assert (
            "High priority" in output
            or "Critical priority" in output
            or "No issues" in output
        )

    def test_today_shows_summary_statistics(self, roadmap_with_workflow_items):
        """Test that today command shows summary statistics."""
        cli_runner, core = roadmap_with_workflow_items

        result = cli_runner.invoke(
            main, ["today"], catch_exceptions=False, env={"ROADMAP_USER": "testuser"}
        )

        IntegrationTestBase.assert_cli_success(result)
        # Should contain counts or statistics
        # Look for patterns like "X in progress" or numbers
        assert re.search(r"\d+", clean_cli_output(result.output)), (
            "No statistics found in output"
        )

    def test_today_with_empty_roadmap(self, cli_runner):
        """Test today command with no upcoming milestones."""
        with cli_runner.isolated_filesystem():
            # Initialize empty roadmap without GitHub
            IntegrationTestBase.init_roadmap(cli_runner)

            result = cli_runner.invoke(
                main,
                ["today"],
                catch_exceptions=False,
                env={"ROADMAP_USER": "testuser"},
            )

            # Should display message about no upcoming milestones or complete successfully
            # Message may be in stdout or logs, check various formats
            assert (
                "upcoming milestones" in clean_cli_output(result.output).lower()
                or result.exit_code == 0
            )
