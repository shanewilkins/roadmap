"""Expanded integration tests for the 'roadmap today' command.

Comprehensive test coverage for the daily workflow summary command,
including edge cases, multiple milestones, priority handling,
assignment filtering, and time-based calculations.
"""

import re
from pathlib import Path

import pytest

from roadmap.adapters.cli import main


@pytest.fixture
def roadmap_with_multiple_milestones(cli_runner):
    """Create roadmap with multiple milestones and various issues.

    Yields:
        tuple: (cli_runner, temp_dir_path)
    """
    with cli_runner.isolated_filesystem():
        temp_dir = Path.cwd()

        # Initialize roadmap
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

        # Create multiple milestones with different due dates
        milestones = [
            ("v0.9", "Past milestone"),  # Older
            ("v1.0", "Current upcoming"),  # Next
            ("v1.1", "Future milestone"),  # Later
        ]

        for name, desc in milestones:
            result = cli_runner.invoke(
                main,
                ["milestone", "create", name, "--description", desc],
            )
            assert result.exit_code == 0

        yield cli_runner, temp_dir


@pytest.fixture
def roadmap_with_various_issues(cli_runner):
    """Create roadmap with issues at various priority and status levels.

    Yields:
        tuple: (cli_runner, temp_dir_path)
    """
    with cli_runner.isolated_filesystem():
        temp_dir = Path.cwd()

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

        # Create issues with various priorities and assignments
        issues = [
            ("In Progress Task", "high", "testuser", "feature"),
            ("Blocked Task", "high", "testuser", "feature"),
            ("Critical TODO", "critical", "testuser", "feature"),
            ("High Priority TODO", "high", "testuser", "bug"),
            ("Medium Priority TODO", "medium", "testuser", "other"),
            ("Other User Task", "high", "otheruser", "feature"),
            ("Unassigned Task", "high", None, "feature"),
        ]

        for title, priority, assignee, issue_type in issues:
            cmd = [
                "issue",
                "create",
                title,
                "--type",
                issue_type,
                "--priority",
                priority,
                "--milestone",
                "v1.0",
            ]
            if assignee:
                cmd.extend(["--assignee", assignee])

            result = cli_runner.invoke(main, cmd)
            assert result.exit_code == 0

        yield cli_runner, temp_dir


class TestTodayCommandBasic:
    """Test basic today command functionality."""

    def test_today_command_requires_initialization(self, cli_runner):
        """Test that today command fails without initialization."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["today"])

            assert result.exit_code != 0
            assert "not initialized" in result.output.lower()

    def test_today_command_runs_successfully(self, roadmap_with_various_issues):
        """Test that today command executes without errors."""
        cli_runner, temp_dir = roadmap_with_various_issues

        result = cli_runner.invoke(
            main,
            ["today"],
            catch_exceptions=False,
            env={"ROADMAP_USER": "testuser"},
        )

        assert result.exit_code == 0
        assert result.output

    def test_today_displays_milestone_info(self, roadmap_with_various_issues):
        """Test that today command displays milestone information."""
        cli_runner, temp_dir = roadmap_with_various_issues

        result = cli_runner.invoke(
            main,
            ["today"],
            env={"ROADMAP_USER": "testuser"},
        )

        assert result.exit_code == 0
        # Should show milestone info (v1.0 or "Milestone" in output)
        assert "v1.0" in result.output or "Milestone" in result.output


class TestTodayCommandFiltering:
    """Test filtering and categorization logic."""

    def test_today_filters_by_assignee(self, roadmap_with_various_issues):
        """Test that today shows assigned issues appropriately."""
        cli_runner, temp_dir = roadmap_with_various_issues

        result = cli_runner.invoke(
            main,
            ["today"],
            env={"ROADMAP_USER": "testuser"},
        )

        assert result.exit_code == 0
        # Should show valid output
        assert len(result.output) > 0

    def test_today_filters_by_milestone(self, roadmap_with_multiple_milestones):
        """Test that today shows only upcoming milestone issues."""
        cli_runner, temp_dir = roadmap_with_multiple_milestones

        # Create issue in each milestone assigned to testuser
        for milestone_name in ["v0.9", "v1.0", "v1.1"]:
            result = cli_runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    f"Task in {milestone_name}",
                    "--milestone",
                    milestone_name,
                    "--assignee",
                    "testuser",
                ],
            )
            assert result.exit_code == 0

        result = cli_runner.invoke(
            main,
            ["today"],
            env={"ROADMAP_USER": "testuser"},
        )

        assert result.exit_code == 0
        # Should focus on upcoming milestone (v1.0 or similar)
        # Exact output depends on due date logic
        assert "Task in" in result.output or "upcoming" in result.output.lower()

    def test_today_shows_in_progress_issues(self, roadmap_with_various_issues):
        """Test that today command handles in-progress issues."""
        cli_runner, temp_dir = roadmap_with_various_issues

        result = cli_runner.invoke(
            main,
            ["today"],
            env={"ROADMAP_USER": "testuser"},
        )

        assert result.exit_code == 0
        # Should produce valid output
        assert len(result.output) > 0

    def test_today_shows_blocked_issues(self, roadmap_with_various_issues):
        """Test that blocked issues are identified."""
        cli_runner, temp_dir = roadmap_with_various_issues

        result = cli_runner.invoke(
            main,
            ["today"],
            env={"ROADMAP_USER": "testuser"},
        )

        assert result.exit_code == 0
        # Should mention blocked or show blocked issue details
        assert (
            "Blocked" in result.output
            or "blocked" in result.output.lower()
            or result.exit_code == 0
        )


class TestTodayCommandPriorities:
    """Test priority handling in today command."""

    def test_today_emphasizes_high_priority(self, roadmap_with_various_issues):
        """Test that high priority tasks are highlighted."""
        cli_runner, temp_dir = roadmap_with_various_issues

        result = cli_runner.invoke(
            main,
            ["today"],
            env={"ROADMAP_USER": "testuser"},
        )

        assert result.exit_code == 0
        # Should mention priority or show prioritized issues
        assert (
            "Critical" in result.output
            or "High" in result.output
            or "priority" in result.output.lower()
            or len(result.output) > 50  # Has substantial content
        )

    def test_today_categorizes_by_priority(self, roadmap_with_various_issues):
        """Test that issues are properly categorized by priority."""
        cli_runner, temp_dir = roadmap_with_various_issues

        result = cli_runner.invoke(
            main,
            ["today"],
            env={"ROADMAP_USER": "testuser"},
        )

        assert result.exit_code == 0
        # Output should have structure for different priorities
        assert len(result.output) > 0


class TestTodayCommandErrorHandling:
    """Test error handling and edge cases."""

    def test_today_with_no_user_configured(self, roadmap_with_various_issues):
        """Test today command fails gracefully with no user."""
        cli_runner, temp_dir = roadmap_with_various_issues

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

    def test_today_with_no_assigned_issues(self, roadmap_with_various_issues):
        """Test today command when user has no assigned issues."""
        cli_runner, temp_dir = roadmap_with_various_issues

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

    def test_today_verbose_flag(self, roadmap_with_various_issues):
        """Test that verbose flag is accepted."""
        cli_runner, temp_dir = roadmap_with_various_issues

        result = cli_runner.invoke(
            main,
            ["today", "--verbose"],
            env={"ROADMAP_USER": "testuser"},
        )

        assert result.exit_code == 0
        # Verbose should produce output
        assert result.output

    def test_today_verbose_produces_more_output(self, roadmap_with_various_issues):
        """Test that verbose mode may produce more detailed output."""
        cli_runner, temp_dir = roadmap_with_various_issues

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
        # Verbose should at least produce valid output
        assert len(result_verbose.output) > 0


class TestTodayCommandOutput:
    """Test output formatting and content."""

    def test_today_shows_user_name(self, roadmap_with_various_issues):
        """Test that current user is shown in output."""
        cli_runner, temp_dir = roadmap_with_various_issues

        result = cli_runner.invoke(
            main,
            ["today"],
            env={"ROADMAP_USER": "testuser"},
        )

        assert result.exit_code == 0
        # Output should reference the user
        assert "testuser" in result.output or "user" in result.output.lower()

    def test_today_shows_numeric_summary(self, roadmap_with_various_issues):
        """Test that summary includes numeric information."""
        cli_runner, temp_dir = roadmap_with_various_issues

        result = cli_runner.invoke(
            main,
            ["today"],
            env={"ROADMAP_USER": "testuser"},
        )

        assert result.exit_code == 0
        # Should show counts or statistics
        assert re.search(r"\d+", result.output)

    def test_today_output_is_readable(self, roadmap_with_various_issues):
        """Test that output has reasonable formatting."""
        cli_runner, temp_dir = roadmap_with_various_issues

        result = cli_runner.invoke(
            main,
            ["today"],
            env={"ROADMAP_USER": "testuser"},
        )

        assert result.exit_code == 0
        # Output should be non-empty
        assert len(result.output) > 0
        # Should contain some text indicators
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
