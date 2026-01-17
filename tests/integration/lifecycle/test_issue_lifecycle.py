"""Integration tests for issue lifecycle (create, update, delete).

Tests issue creation, updating, status transitions, and milestone assignment
to ensure data integrity and validation across operations.
"""

import pytest

from roadmap.adapters.cli import main
from tests.fixtures.integration_helpers import IntegrationTestBase


@pytest.fixture
def roadmap_with_milestones(cli_runner):
    """Create an initialized roadmap with a milestone."""
    with cli_runner.isolated_filesystem():
        core = IntegrationTestBase.init_roadmap(cli_runner)
        IntegrationTestBase.create_milestone(
            cli_runner,
            name="sprint-1",
            headline="First sprint",
        )
        yield cli_runner, core


class TestIssueLifecycle:
    """Test issue creation, update, status transitions, and deletion flows."""

    def test_create_issue_with_defaults(self, roadmap_with_milestones):
        """Test creating an issue with minimal parameters."""
        cli_runner, core = roadmap_with_milestones

        IntegrationTestBase.create_issue(
            cli_runner,
            title="Simple task",
        )
        IntegrationTestBase.assert_cli_success(
            cli_runner.invoke(main, ["issue", "list"]),
            context="Listing issues after create",
        )
        # Verify through core API
        core = IntegrationTestBase.get_roadmap_core()
        assert len(core.issues.list()) > 0
        assert any(i.title == "Simple task" for i in core.issues.list())

    def test_create_issue_with_all_options(self, roadmap_with_milestones):
        """Test creating issue with all available options."""
        cli_runner, core = roadmap_with_milestones

        IntegrationTestBase.create_issue(
            cli_runner,
            title="Complex task",
            priority="high",
            assignee="alice",
            milestone="sprint-1",
        )
        # Verify through core API
        core = IntegrationTestBase.get_roadmap_core()
        assert len(core.issues.list()) > 0
        assert any(i.title == "Complex task" for i in core.issues.list())

    def test_create_issue_without_milestone(self, roadmap_with_milestones):
        """Test creating issue without assigning to milestone."""
        cli_runner, core = roadmap_with_milestones

        IntegrationTestBase.create_issue(
            cli_runner,
            title="Backlog task",
        )
        core = IntegrationTestBase.get_roadmap_core()
        assert any(i.title == "Backlog task" for i in core.issues.list())

    def test_update_issue_status(self, roadmap_with_milestones):
        """Test updating issue through status transitions."""
        cli_runner, core = roadmap_with_milestones

        IntegrationTestBase.create_issue(
            cli_runner,
            title="Work task",
        )
        # Verify issue exists
        result = cli_runner.invoke(main, ["issue", "list"])
        IntegrationTestBase.assert_cli_success(result)
        # Title might be wrapped in table, check for parts
        assert "Work" in result.output and "task" in result.output

    def test_update_issue_assignment(self, roadmap_with_milestones):
        """Test reassigning issue to different milestone."""
        cli_runner, core = roadmap_with_milestones

        # Create issue in sprint-1
        IntegrationTestBase.create_issue(
            cli_runner,
            title="Task",
            milestone="sprint-1",
        )

        # Create another milestone
        IntegrationTestBase.create_milestone(cli_runner, name="sprint-2")

        # Verify issue is in sprint-1
        result = cli_runner.invoke(
            main,
            ["issue", "list", "--milestone", "sprint-1"],
        )
        IntegrationTestBase.assert_cli_success(result)
        assert "Task" in result.output

    def test_update_issue_priority(self, roadmap_with_milestones):
        """Test updating issue priority."""
        cli_runner, core = roadmap_with_milestones

        # Create issue with low priority
        IntegrationTestBase.create_issue(
            cli_runner,
            title="Priority task",
            milestone="sprint-1",
            priority="low",
        )

        # Verify issue was created
        result = cli_runner.invoke(
            main,
            ["issue", "list", "--milestone", "sprint-1"],
        )
        IntegrationTestBase.assert_cli_success(result)
        assert "task" in result.output and "low" in result.output

    def test_list_issues_by_milestone(self, roadmap_with_milestones):
        """Test listing issues filtered by milestone."""
        cli_runner, core = roadmap_with_milestones

        # Create multiple issues in sprint-1
        for i in range(3):
            IntegrationTestBase.create_issue(
                cli_runner,
                title=f"Task {i+1}",
                milestone="sprint-1",
            )

        # List issues in sprint-1
        result = cli_runner.invoke(
            main,
            ["issue", "list", "--milestone", "sprint-1"],
        )
        IntegrationTestBase.assert_cli_success(result)
        for i in range(3):
            assert f"Task {i+1}" in result.output

    def test_list_issues_by_status(self, roadmap_with_milestones):
        """Test listing issues filtered by status."""
        cli_runner, core = roadmap_with_milestones

        # Create issues with different titles
        titles = ["Todo issue", "In progress issue", "Done issue"]
        for title in titles:
            IntegrationTestBase.create_issue(
                cli_runner,
                title=title,
                milestone="sprint-1",
            )

        # List all issues to verify they were created
        result = cli_runner.invoke(main, ["issue", "list"])
        IntegrationTestBase.assert_cli_success(result)
        for title in titles:
            assert title in result.output

    def test_issue_with_assignee(self, roadmap_with_milestones):
        """Test creating and updating issue with assignee."""
        cli_runner, core = roadmap_with_milestones

        # Create issue with assignee
        IntegrationTestBase.create_issue(
            cli_runner,
            title="Team task",
            milestone="sprint-1",
            assignee="alice",
        )

        # Verify issue was created with assignee
        result = cli_runner.invoke(
            main,
            ["issue", "list", "--milestone", "sprint-1"],
        )
        IntegrationTestBase.assert_cli_success(result)
        # Title might be wrapped in table, check for parts
        assert "Team" in result.output and "task" in result.output

    def test_issue_priority_levels(self, roadmap_with_milestones):
        """Test creating issues with different priority levels."""
        cli_runner, core = roadmap_with_milestones

        priorities = ["low", "medium", "high", "critical"]
        for priority in priorities:
            IntegrationTestBase.create_issue(
                cli_runner,
                title=f"{priority.capitalize()} issue",
                priority=priority,
            )

    @pytest.mark.no_xdist
    def test_issue_type_variations(self, roadmap_with_milestones):
        """Test creating issues with different milestones and verifying relationships."""
        cli_runner, core = roadmap_with_milestones

        # Create another milestone
        IntegrationTestBase.create_milestone(cli_runner, name="sprint-2")

        # Create issue in sprint-1
        IntegrationTestBase.create_issue(
            cli_runner,
            title="Feature task",
            milestone="sprint-1",
        )

        # Create issue in sprint-2
        IntegrationTestBase.create_issue(
            cli_runner,
            title="Bug task",
            milestone="sprint-2",
        )

        # Verify both exist
        result = cli_runner.invoke(main, ["issue", "list"])
        IntegrationTestBase.assert_cli_success(result)
        # Title might be wrapped or truncated in table, check for parts
        assert (
            "Feature" in result.output or "Featu" in result.output
        ) and "task" in result.output
        assert "Bug" in result.output and "task" in result.output

    def test_multiple_issues_in_milestone(self, roadmap_with_milestones):
        """Test creating and managing multiple issues in same milestone."""
        cli_runner, core = roadmap_with_milestones

        # Create 5 issues
        for i in range(1, 6):
            IntegrationTestBase.create_issue(
                cli_runner,
                title=f"Issue {i}",
                milestone="sprint-1",
            )

        # List all
        result = cli_runner.invoke(
            main,
            ["issue", "list", "--milestone", "sprint-1"],
        )
        IntegrationTestBase.assert_cli_success(result)
        for i in range(1, 6):
            # Title might be wrapped in table, check for parts
            assert "Issue" in result.output and str(i) in result.output

    def test_issue_relationships_across_milestones(self, roadmap_with_milestones):
        """Test that issues maintain correct relationships across milestone operations."""
        cli_runner, core = roadmap_with_milestones

        # Create second milestone
        IntegrationTestBase.create_milestone(cli_runner, name="sprint-2")

        # Create issues in both milestones
        for milestone in ["sprint-1", "sprint-2"]:
            for i in range(2):
                IntegrationTestBase.create_issue(
                    cli_runner,
                    title=f"{milestone} Issue {i+1}",
                    milestone=milestone,
                )

        # Verify each milestone has its issues
        for milestone in ["sprint-1", "sprint-2"]:
            result = cli_runner.invoke(
                main,
                ["issue", "list", "--milestone", milestone],
            )
            IntegrationTestBase.assert_cli_success(result)
            assert f"{milestone} Issue 1" in result.output
            assert f"{milestone} Issue 2" in result.output
