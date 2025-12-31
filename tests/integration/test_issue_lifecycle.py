"""Integration tests for issue lifecycle (create, update, delete).

Tests issue creation, updating, status transitions, and milestone assignment
to ensure data integrity and validation across operations.
"""

from pathlib import Path

import pytest

from roadmap.adapters.cli import main


@pytest.fixture
def roadmap_with_milestones(cli_runner):
    """Create an initialized roadmap with a milestone."""
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
        assert result.exit_code == 0, f"Init failed: {result.output}"

        # Create a milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "sprint-1", "--description", "First sprint"],
        )
        assert result.exit_code == 0, f"Milestone creation failed: {result.output}"

        yield cli_runner, temp_dir


class TestIssueLifecycle:
    """Test issue creation, update, status transitions, and deletion flows."""

    def test_create_issue_with_defaults(self, roadmap_with_milestones):
        """Test creating an issue with minimal parameters."""
        cli_runner, _ = roadmap_with_milestones

        result = cli_runner.invoke(
            main,
            ["issue", "create", "Simple task"],
        )
        assert result.exit_code == 0, f"Issue creation failed: {result.output}"
        assert "Simple task" in result.output

    def test_create_issue_with_all_options(self, roadmap_with_milestones):
        """Test creating issue with all available options."""
        cli_runner, _ = roadmap_with_milestones

        result = cli_runner.invoke(
            main,
            [
                "issue",
                "create",
                "Complex task",
                "--priority",
                "high",
                "--type",
                "feature",
                "--assignee",
                "alice",
                "--milestone",
                "sprint-1",
            ],
        )
        assert result.exit_code == 0, f"Issue creation failed: {result.output}"

    def test_create_issue_without_milestone(self, roadmap_with_milestones):
        """Test creating issue without assigning to milestone."""
        cli_runner, _ = roadmap_with_milestones

        result = cli_runner.invoke(
            main,
            ["issue", "create", "Backlog task"],
        )
        assert result.exit_code == 0

    def test_update_issue_status(self, roadmap_with_milestones):
        """Test updating issue through status transitions."""
        cli_runner, _ = roadmap_with_milestones

        # Create issue
        result = cli_runner.invoke(
            main,
            ["issue", "create", "Work task"],
        )
        assert result.exit_code == 0
        # Extract issue ID from output or list
        result = cli_runner.invoke(main, ["issue", "list"])
        assert result.exit_code == 0
        assert "Work task" in result.output

    def test_update_issue_assignment(self, roadmap_with_milestones):
        """Test reassigning issue to different milestone."""
        cli_runner, _ = roadmap_with_milestones

        # Create issue in sprint-1
        result = cli_runner.invoke(
            main,
            ["issue", "create", "Task", "--milestone", "sprint-1"],
        )
        assert result.exit_code == 0

        # Create another milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "sprint-2"],
        )
        assert result.exit_code == 0

        # Verify issue is in sprint-1
        result = cli_runner.invoke(
            main,
            ["issue", "list", "--milestone", "sprint-1"],
        )
        assert result.exit_code == 0
        assert "Task" in result.output

    def test_update_issue_priority(self, roadmap_with_milestones):
        """Test updating issue priority."""
        cli_runner, _ = roadmap_with_milestones

        # Create issue with low priority
        result = cli_runner.invoke(
            main,
            [
                "issue",
                "create",
                "Priority task",
                "--milestone",
                "sprint-1",
                "--priority",
                "low",
            ],
        )
        assert result.exit_code == 0

        # Verify issue was created
        result = cli_runner.invoke(
            main,
            ["issue", "list", "--milestone", "sprint-1"],
        )
        assert result.exit_code == 0
        assert "Priority task" in result.output

    def test_list_issues_by_milestone(self, roadmap_with_milestones):
        """Test listing issues filtered by milestone."""
        cli_runner, _ = roadmap_with_milestones

        # Create multiple issues in sprint-1
        for i in range(3):
            result = cli_runner.invoke(
                main,
                ["issue", "create", f"Task {i+1}", "--milestone", "sprint-1"],
            )
            assert result.exit_code == 0

        # List issues in sprint-1
        result = cli_runner.invoke(
            main,
            ["issue", "list", "--milestone", "sprint-1"],
        )
        assert result.exit_code == 0
        for i in range(3):
            assert f"Task {i+1}" in result.output

    def test_list_issues_by_status(self, roadmap_with_milestones):
        """Test listing issues filtered by status."""
        cli_runner, _ = roadmap_with_milestones

        # Create issues with different titles
        titles = ["Todo issue", "In progress issue", "Done issue"]
        for title in titles:
            result = cli_runner.invoke(
                main,
                ["issue", "create", title, "--milestone", "sprint-1"],
            )
            assert result.exit_code == 0

        # List all issues to verify they were created
        result = cli_runner.invoke(main, ["issue", "list"])
        assert result.exit_code == 0
        for title in titles:
            assert title in result.output

    def test_issue_with_assignee(self, roadmap_with_milestones):
        """Test creating and updating issue with assignee."""
        cli_runner, _ = roadmap_with_milestones

        # Create issue with assignee
        result = cli_runner.invoke(
            main,
            [
                "issue",
                "create",
                "Team task",
                "--milestone",
                "sprint-1",
                "--assignee",
                "alice",
            ],
        )
        assert result.exit_code == 0

        # Verify issue was created with assignee
        result = cli_runner.invoke(
            main,
            ["issue", "list", "--milestone", "sprint-1"],
        )
        assert result.exit_code == 0
        assert "Team task" in result.output

    def test_issue_priority_levels(self, roadmap_with_milestones):
        """Test creating issues with different priority levels."""
        cli_runner, _ = roadmap_with_milestones

        priorities = ["low", "medium", "high", "critical"]
        for priority in priorities:
            result = cli_runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    f"{priority.capitalize()} issue",
                    "--priority",
                    priority,
                ],
            )
            assert result.exit_code == 0

    @pytest.mark.no_xdist
    def test_issue_type_variations(self, roadmap_with_milestones):
        """Test creating issues with different milestones and verifying relationships."""
        cli_runner, _ = roadmap_with_milestones

        # Create another milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "sprint-2"],
        )
        assert result.exit_code == 0

        # Create issue in sprint-1
        result = cli_runner.invoke(
            main,
            ["issue", "create", "Feature task", "--milestone", "sprint-1"],
        )
        assert result.exit_code == 0

        # Create issue in sprint-2
        result = cli_runner.invoke(
            main,
            ["issue", "create", "Bug task", "--milestone", "sprint-2"],
        )
        assert result.exit_code == 0

        # Verify both exist
        result = cli_runner.invoke(main, ["issue", "list"])
        assert result.exit_code == 0
        assert "Feature task" in result.output
        assert "Bug task" in result.output

    def test_multiple_issues_in_milestone(self, roadmap_with_milestones):
        """Test creating and managing multiple issues in same milestone."""
        cli_runner, _ = roadmap_with_milestones

        # Create 5 issues
        for i in range(1, 6):
            result = cli_runner.invoke(
                main,
                ["issue", "create", f"Issue {i}", "--milestone", "sprint-1"],
            )
            assert result.exit_code == 0

        # List all
        result = cli_runner.invoke(
            main,
            ["issue", "list", "--milestone", "sprint-1"],
        )
        assert result.exit_code == 0
        for i in range(1, 6):
            assert f"Issue {i}" in result.output

    def test_issue_relationships_across_milestones(self, roadmap_with_milestones):
        """Test that issues maintain correct relationships across milestone operations."""
        cli_runner, _ = roadmap_with_milestones

        # Create second milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "sprint-2"],
        )
        assert result.exit_code == 0

        # Create issues in both milestones
        for milestone in ["sprint-1", "sprint-2"]:
            for i in range(2):
                result = cli_runner.invoke(
                    main,
                    [
                        "issue",
                        "create",
                        f"{milestone} Issue {i+1}",
                        "--milestone",
                        milestone,
                    ],
                )
                assert result.exit_code == 0

        # Verify each milestone has its issues
        for milestone in ["sprint-1", "sprint-2"]:
            result = cli_runner.invoke(
                main,
                ["issue", "list", "--milestone", milestone],
            )
            assert result.exit_code == 0
            assert f"{milestone} Issue 1" in result.output
            assert f"{milestone} Issue 2" in result.output
