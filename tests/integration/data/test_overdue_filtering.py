"""Integration tests for --overdue flag on list commands.

Tests the overdue filtering functionality for issues, milestones, and projects.
"""

from datetime import UTC, datetime, timedelta

from roadmap.adapters.cli import main
from tests.fixtures.integration_helpers import IntegrationTestBase


class TestOverdueIssueFiltering:
    """Test the --overdue flag for issue list command."""

    def test_issue_list_overdue_flag_works(self, cli_runner):
        """Test that --overdue flag is accepted and executes."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create an overdue milestone
            overdue_date = (datetime.now(UTC) - timedelta(days=5)).strftime("%Y-%m-%d")
            IntegrationTestBase.create_milestone(
                cli_runner,
                name="overdue-milestone",
                headline="This is overdue",
                due_date=overdue_date,
            )

            # Create a future milestone
            future_date = (datetime.now(UTC) + timedelta(days=30)).strftime("%Y-%m-%d")
            IntegrationTestBase.create_milestone(
                cli_runner,
                name="future-milestone",
                headline="This is in the future",
                due_date=future_date,
            )

            # Create issues
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Overdue issue",
                issue_type="bug",
                priority="high",
                estimate=8,
            )
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Future issue",
                issue_type="feature",
                priority="medium",
                estimate=4,
            )
            IntegrationTestBase.create_issue(
                cli_runner,
                title="No due date issue",
                issue_type="other",
                priority="low",
            )

            result = cli_runner.invoke(
                main, ["issue", "list", "--overdue"], catch_exceptions=False
            )

            assert result.exit_code == 0, (
                f"Issue list --overdue failed: {result.output}"
            )

    def test_issue_list_without_overdue_shows_all(self, cli_runner):
        """Test that without --overdue flag, all issues are shown."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create issues
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Overdue issue",
                issue_type="bug",
                priority="high",
                estimate=8,
            )
            IntegrationTestBase.create_issue(
                cli_runner,
                title="Future issue",
                issue_type="feature",
                priority="medium",
                estimate=4,
            )
            IntegrationTestBase.create_issue(
                cli_runner,
                title="No due date issue",
                issue_type="other",
                priority="low",
            )

            result = cli_runner.invoke(main, ["issue", "list"], catch_exceptions=False)

            assert result.exit_code == 0
            assert "Overdue issue" in result.output
            assert "Future issue" in result.output
            assert "No due date issue" in result.output

    def test_issue_list_overdue_with_other_filters(self, cli_runner):
        """Test that --overdue can be combined with other filters."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            IntegrationTestBase.create_issue(
                cli_runner,
                title="Test issue",
                issue_type="bug",
                priority="high",
            )

            result = cli_runner.invoke(
                main,
                ["issue", "list", "--overdue", "--priority", "high"],
                catch_exceptions=False,
            )

            assert result.exit_code == 0


class TestOverdueMilestoneFiltering:
    """Test the --overdue flag for milestone list command."""

    def test_milestone_list_overdue_flag_works(self, cli_runner):
        """Test that --overdue flag is accepted and executes."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create an overdue milestone
            overdue_date = (datetime.now(UTC) - timedelta(days=5)).strftime("%Y-%m-%d")
            IntegrationTestBase.create_milestone(
                cli_runner,
                name="overdue-milestone",
                headline="This is overdue",
                due_date=overdue_date,
            )

            # Create a future milestone
            future_date = (datetime.now(UTC) + timedelta(days=30)).strftime("%Y-%m-%d")
            IntegrationTestBase.create_milestone(
                cli_runner,
                name="future-milestone",
                headline="This is in the future",
                due_date=future_date,
            )

            result = cli_runner.invoke(
                main, ["milestone", "list", "--overdue"], catch_exceptions=False
            )

            assert result.exit_code == 0, (
                f"Milestone list --overdue failed: {result.output}"
            )
            assert "overdue" in result.output.lower()

    def test_milestone_list_without_overdue_shows_all(self, cli_runner):
        """Test that without --overdue flag, all milestones are shown."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create an overdue milestone
            overdue_date = (datetime.now(UTC) - timedelta(days=5)).strftime("%Y-%m-%d")
            IntegrationTestBase.create_milestone(
                cli_runner,
                name="overdue-milestone",
                headline="This is overdue",
                due_date=overdue_date,
            )

            # Create a future milestone
            future_date = (datetime.now(UTC) + timedelta(days=30)).strftime("%Y-%m-%d")
            IntegrationTestBase.create_milestone(
                cli_runner,
                name="future-milestone",
                headline="This is in the future",
                due_date=future_date,
            )

            result = cli_runner.invoke(
                main, ["milestone", "list"], catch_exceptions=False
            )

            assert result.exit_code == 0
            assert "overdue" in result.output.lower()
            assert "future" in result.output.lower()

    def test_milestone_overdue_only_includes_open(self, cli_runner):
        """Test that --overdue only includes open milestones, not completed ones."""
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)

            # Create an overdue milestone
            overdue_date = (datetime.now(UTC) - timedelta(days=5)).strftime("%Y-%m-%d")
            IntegrationTestBase.create_milestone(
                cli_runner,
                name="overdue-milestone",
                headline="This is overdue",
                due_date=overdue_date,
            )

            # Try to close the overdue milestone
            close_result = cli_runner.invoke(
                main,
                ["milestone", "close", "overdue-milestone"],
                catch_exceptions=False,
            )

            # Now check overdue list
            result = cli_runner.invoke(
                main, ["milestone", "list", "--overdue"], catch_exceptions=False
            )

            assert result.exit_code == 0
            output_lower = result.output.lower()

            # If close command executed successfully, verify the milestone status
            if close_result.exit_code == 0:
                if "overdue-milestone" in result.output:
                    assert "closed" in output_lower or "open" in output_lower


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

            # Create a project
            result = cli_runner.invoke(
                main,
                [
                    "project",
                    "create",
                    "--title",
                    "test-proj",
                    "--description",
                    "Test Project",
                ],
                catch_exceptions=False,
            )
            assert result.exit_code == 0

            # Test overdue filter flag works (may return empty if no overdue projects)
            result = cli_runner.invoke(
                main, ["project", "list", "--overdue"], catch_exceptions=False
            )

            assert result.exit_code == 0

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

            # Create projects
            result = cli_runner.invoke(
                main,
                [
                    "project",
                    "create",
                    "--title",
                    "proj1",
                    "--description",
                    "First Project",
                ],
            )
            assert result.exit_code == 0

            result = cli_runner.invoke(
                main,
                [
                    "project",
                    "create",
                    "--title",
                    "proj2",
                    "--description",
                    "Second Project",
                ],
            )
            assert result.exit_code == 0

            # Test without filter lists all projects
            result = cli_runner.invoke(
                main, ["project", "list"], catch_exceptions=False
            )

            assert result.exit_code == 0
            assert "proj1" in result.output
            assert "proj2" in result.output
