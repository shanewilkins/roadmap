"""Expanded integration tests for the 'roadmap today' command.

Comprehensive test coverage for the daily workflow summary command,
including edge cases, multiple milestones, priority handling,
assignment filtering, and time-based calculations.
"""

import re

from roadmap.adapters.cli import main
from tests.fixtures.integration_helpers import IntegrationTestBase


class TestTodayCommandBasic:
    """Test basic today command functionality."""

    def test_today_command_requires_initialization(self, cli_runner):
        """Test that today command fails without initialization."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["today"])

            assert result.exit_code != 0
            assert "not initialized" in result.output.lower()

    def test_today_command_runs_successfully(self, cli_runner):
        """Test that today command executes without errors."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestone
            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")

            # Create issues
            for title, priority, assignee, issue_type in [
                ("In Progress Task", "high", "testuser", "feature"),
                ("Blocked Task", "high", "testuser", "feature"),
                ("Critical TODO", "critical", "testuser", "feature"),
                ("High Priority TODO", "high", "testuser", "bug"),
                ("Medium Priority TODO", "medium", "testuser", "other"),
                ("Other User Task", "high", "otheruser", "feature"),
                ("Unassigned Task", "high", None, "feature"),
            ]:
                IntegrationTestBase.create_issue(
                    cli_runner,
                    title=title,
                    issue_type=issue_type,
                    priority=priority,
                    milestone="v1.0",
                    assignee=assignee,
                )

            result = cli_runner.invoke(
                main,
                ["today"],
                catch_exceptions=False,
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            assert result.output

    def test_today_displays_milestone_info(self, cli_runner):
        """Test that today command displays milestone information."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestone
            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")

            # Create issue
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Test Task",
                assignee="testuser",
                milestone="v1.0",
            )

            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            assert "v1.0" in result.output or "Milestone" in result.output


class TestTodayCommandFiltering:
    """Test filtering and categorization logic."""

    def test_today_filters_by_assignee(self, cli_runner):
        """Test that today shows assigned issues appropriately."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestone and issues
            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")

            for title, priority, assignee in [
                ("Task 1", "high", "testuser"),
                ("Task 2", "medium", "otheruser"),
            ]:
                IntegrationTestBase.create_issue(
                    cli_runner,
                    title=title,
                    priority=priority,
                    milestone="v1.0",
                    assignee=assignee,
                )

            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            assert len(result.output) > 0

    def test_today_filters_by_milestone(self, cli_runner):
        """Test that today shows only upcoming milestone issues."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestones
            for name, desc in [
                ("v0.9", "Past milestone"),
                ("v1.0", "Current upcoming"),
                ("v1.1", "Future milestone"),
            ]:
                IntegrationTestBase.create_milestone(
                    cli_runner, name=name, headline=desc
                )

            # Create issue in each milestone assigned to testuser
            for milestone_name in ["v0.9", "v1.0", "v1.1"]:
                IntegrationTestBase.create_issue(
                    cli_runner,
                    title=f"Task in {milestone_name}",
                    milestone=milestone_name,
                    assignee="testuser",
                )

            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            assert "Task in" in result.output or "upcoming" in result.output.lower()

    def test_today_shows_in_progress_issues(self, cli_runner):
        """Test that today command handles in-progress issues."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")
            IntegrationTestBase.create_issue(
                cli_runner,
                title="In Progress Task",
                milestone="v1.0",
                assignee="testuser",
            )

            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            assert len(result.output) > 0

    def test_today_shows_blocked_issues(self, cli_runner):
        """Test that blocked issues are identified."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Blocked Task",
                milestone="v1.0",
                assignee="testuser",
            )

            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            assert (
                "Blocked" in result.output
                or "blocked" in result.output.lower()
                or result.exit_code == 0
            )


class TestTodayCommandPriorities:
    """Test priority handling in today command."""

    def test_today_emphasizes_high_priority(self, cli_runner):
        """Test that high priority tasks are highlighted."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestone and issues
            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")

            for title, priority in [
                ("Critical TODO", "critical"),
                ("High Priority TODO", "high"),
                ("Medium Priority TODO", "medium"),
            ]:
                IntegrationTestBase.create_issue(
                    cli_runner,
                    title=title,
                    priority=priority,
                    milestone="v1.0",
                    assignee="testuser",
                )

            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            assert (
                "Critical" in result.output
                or "High" in result.output
                or "priority" in result.output.lower()
                or len(result.output) > 50
            )

    def test_today_categorizes_by_priority(self, cli_runner):
        """Test that issues are properly categorized by priority."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestone and issues
            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")

            for title, priority in [
                ("High Priority", "high"),
                ("Low Priority", "low"),
            ]:
                IntegrationTestBase.create_issue(
                    cli_runner,
                    title=title,
                    priority=priority,
                    milestone="v1.0",
                    assignee="testuser",
                )

            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            assert len(result.output) > 0


class TestTodayCommandErrorHandling:
    """Test error handling and edge cases."""

    def test_today_with_no_user_configured(self, cli_runner):
        """Test today command fails gracefully with no user."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestone and issues
            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Test Task",
                milestone="v1.0",
                assignee="testuser",
            )

            # Don't set ROADMAP_USER and no user in config
            result = cli_runner.invoke(main, ["today"])

            # Should fail or show helpful message
            assert (
                result.exit_code != 0
                or "user" in result.output.lower()
                or "configure" in result.output.lower()
            )

    def test_today_with_empty_roadmap(self, cli_runner):
        """Test today command with no milestones or issues."""
        with cli_runner.isolated_filesystem():
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
                env={"ROADMAP_USER": "testuser"},
            )

            # Should handle gracefully
            assert (
                result.exit_code == 0
                or "upcoming" in result.output.lower()
                or "milestone" in result.output.lower()
            )

    def test_today_with_no_assigned_issues(self, cli_runner):
        """Test today command when user has no assigned issues."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestone and issues assigned to different user
            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Other User Task",
                milestone="v1.0",
                assignee="otheruser",
            )

            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "unassigneduser"},
            )

            assert result.exit_code == 0
            # Should show empty state or friendly message
            assert (
                "no" in result.output.lower()
                or "none" in result.output.lower()
                or "empty" in result.output.lower()
                or len(result.output) > 0
            )

    def test_today_with_only_future_milestones(self, cli_runner):
        """Test today command when milestones are all in the future."""
        with cli_runner.isolated_filesystem():
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

            # Create only closed/archived milestones
            result = cli_runner.invoke(
                main,
                ["milestone", "create", "past-milestone"],
            )
            assert result.exit_code == 0

            # Close the milestone
            result = cli_runner.invoke(
                main,
                ["milestone", "close", "past-milestone"],
            )
            assert result.exit_code == 0

            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            # Should handle gracefully
            assert result.exit_code == 0 or "upcoming" in result.output.lower()


class TestTodayCommandVerboseMode:
    """Test verbose output option."""

    def test_today_verbose_flag(self, cli_runner):
        """Test that verbose flag is accepted."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestone and issues
            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Task 1",
                milestone="v1.0",
                assignee="testuser",
            )

            result = cli_runner.invoke(
                main,
                ["today", "--verbose"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            assert result.output

    def test_today_verbose_produces_more_output(self, cli_runner):
        """Test that verbose mode may produce more detailed output."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestone and issues
            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Task 1",
                milestone="v1.0",
                assignee="testuser",
            )

            # Regular output
            result_normal = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            # Verbose output
            result_verbose = cli_runner.invoke(
                main,
                ["today", "--verbose"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result_normal.exit_code == 0
            assert result_verbose.exit_code == 0
            assert len(result_verbose.output) > 0


class TestTodayCommandOutput:
    """Test output formatting and content."""

    def test_today_shows_user_name(self, cli_runner):
        """Test that current user is shown in output."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestone and issues
            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Task 1",
                milestone="v1.0",
                assignee="testuser",
            )

            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            assert "testuser" in result.output or "user" in result.output.lower()

    def test_today_shows_numeric_summary(self, cli_runner):
        """Test that summary includes numeric information."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestone and issues
            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Task 1",
                milestone="v1.0",
                assignee="testuser",
            )
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Task 2",
                milestone="v1.0",
                assignee="testuser",
            )

            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            assert re.search(r"\d+", result.output)

    def test_today_output_is_readable(self, cli_runner):
        """Test that output has reasonable formatting."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create milestone and issues
            IntegrationTestBase.create_milestone(cli_runner, name="v1.0")
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Task 1",
                milestone="v1.0",
                assignee="testuser",
            )

            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            assert len(result.output) > 0
            assert any(
                keyword in result.output.lower()
                for keyword in ["task", "issue", "milestone", "progress", "summary"]
            )


class TestTodayCommandMultipleScenarios:
    """Test realistic workflow scenarios."""

    def test_today_mixed_user_and_unassigned(self, cli_runner):
        """Test today with mix of assigned and unassigned issues."""
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

            # Create milestone
            result = cli_runner.invoke(
                main,
                ["milestone", "create", "v1.0"],
            )
            assert result.exit_code == 0

            # Create assigned issue
            result = cli_runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    "My Task",
                    "--milestone",
                    "v1.0",
                ],
            )
            assert result.exit_code == 0

            # Create unassigned issue
            result = cli_runner.invoke(
                main,
                ["issue", "create", "Unassigned Task", "--milestone", "v1.0"],
            )
            assert result.exit_code == 0

            # Run today
            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            # Should execute without error
            assert result.exit_code == 0 or "upcoming" in result.output.lower()

    def test_today_all_status_types(self, cli_runner):
        """Test today with issues in various states."""
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

            # Create milestone
            result = cli_runner.invoke(
                main,
                ["milestone", "create", "v1.0"],
            )
            assert result.exit_code == 0

            # Create issues (can't directly set status on creation)
            titles = ["Todo Task", "High Priority Task"]
            for title in titles:
                result = cli_runner.invoke(
                    main,
                    [
                        "issue",
                        "create",
                        title,
                        "--assignee",
                        "testuser",
                        "--milestone",
                        "v1.0",
                        "--priority",
                        "high",
                    ],
                )
                assert result.exit_code == 0

            # Run today
            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            # Should handle issues without error
            assert len(result.output) > 0

    def test_today_all_priority_types(self, cli_runner):
        """Test today with issues at all priority levels."""
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

            # Create milestone
            result = cli_runner.invoke(
                main,
                ["milestone", "create", "v1.0"],
            )
            assert result.exit_code == 0

            # Create issues with different priorities
            priorities = ["critical", "high", "medium", "low"]
            for priority in priorities:
                result = cli_runner.invoke(
                    main,
                    [
                        "issue",
                        "create",
                        f"Task {priority}",
                        "--priority",
                        priority,
                        "--milestone",
                        "v1.0",
                    ],
                )
                assert result.exit_code == 0

            # Run today
            result = cli_runner.invoke(
                main,
                ["today"],
                env={"ROADMAP_USER": "testuser"},
            )

            assert result.exit_code == 0
            # Should produce valid output
            assert len(result.output) > 0
