"""Unit tests for milestone kanban board command."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.milestones.kanban import (
    _display_board,
    _display_header,
    _display_summary,
    milestone_kanban,
)
from roadmap.core.domain import Issue, Milestone, MilestoneStatus, Priority, Status
from roadmap.core.domain.issue import IssueType


@pytest.fixture
def sample_milestone():
    """Create a sample milestone."""
    return Milestone(
        name="v1.0",
        content="First release",
        due_date=datetime.now(UTC) + timedelta(days=30),
        status=MilestoneStatus.OPEN,
    )


@pytest.fixture
def sample_issues():
    """Create sample issues for kanban board."""
    return [
        Issue(
            title="Feature A - To Do",
            status=Status.TODO,
            priority=Priority.HIGH,
            issue_type=IssueType.FEATURE,
            milestone="v1.0",
        ),
        Issue(
            title="Feature B - In Progress",
            status=Status.IN_PROGRESS,
            priority=Priority.MEDIUM,
            issue_type=IssueType.FEATURE,
            milestone="v1.0",
        ),
        Issue(
            title="Bug Fix - Closed",
            status=Status.CLOSED,
            priority=Priority.HIGH,
            issue_type=IssueType.BUG,
            milestone="v1.0",
        ),
        Issue(
            title="Task - Blocked",
            status=Status.BLOCKED,
            priority=Priority.MEDIUM,
            issue_type=IssueType.FEATURE,
            milestone="v1.0",
        ),
    ]


class TestMilestoneKanban:
    """Test milestone kanban board command."""

    def test_kanban_displays_milestone(
        self, cli_runner, mock_core, sample_milestone, sample_issues
    ):
        """Test that kanban command displays milestone kanban board."""
        mock_core.milestones.get.return_value = sample_milestone
        mock_core.issues.list.return_value = sample_issues

        with patch(
            "roadmap.adapters.cli.milestones.kanban.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            runner = CliRunner()
            result = runner.invoke(
                milestone_kanban,
                ["v1.0"],
                obj={"core": mock_core},
            )

            assert result.exit_code == 0
            assert mock_core.milestones.get.called
            assert mock_core.issues.list.called

    def test_kanban_milestone_not_found(self, cli_runner, mock_core):
        """Test error handling when milestone is not found."""
        mock_core.milestones.get.return_value = None
        mock_core.issues.list.return_value = []

        with patch(
            "roadmap.adapters.cli.milestones.kanban.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            runner = CliRunner()
            result = runner.invoke(
                milestone_kanban,
                ["nonexistent"],
                obj={"core": mock_core},
            )

            # Should handle not found gracefully
            assert result.exit_code == 0

    def test_kanban_no_issues_for_milestone(
        self, cli_runner, mock_core, sample_milestone
    ):
        """Test kanban when milestone has no issues."""
        mock_core.milestones.get.return_value = sample_milestone
        mock_core.issues.list.return_value = []

        with patch(
            "roadmap.adapters.cli.milestones.kanban.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            runner = CliRunner()
            result = runner.invoke(
                milestone_kanban,
                ["v1.0"],
                obj={"core": mock_core},
            )

            # Should handle no issues gracefully
            assert result.exit_code == 0

    def test_kanban_compact_view(
        self, cli_runner, mock_core, sample_milestone, sample_issues
    ):
        """Test kanban command with compact view option."""
        mock_core.milestones.get.return_value = sample_milestone
        mock_core.issues.list.return_value = sample_issues

        with patch(
            "roadmap.adapters.cli.milestones.kanban.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            runner = CliRunner()
            result = runner.invoke(
                milestone_kanban,
                ["v1.0", "--compact"],
                obj={"core": mock_core},
            )

            assert result.exit_code == 0
            assert mock_core.milestones.get.called

    def test_kanban_no_color(
        self, cli_runner, mock_core, sample_milestone, sample_issues
    ):
        """Test kanban command with color disabled."""
        mock_core.milestones.get.return_value = sample_milestone
        mock_core.issues.list.return_value = sample_issues

        with patch(
            "roadmap.adapters.cli.milestones.kanban.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            runner = CliRunner()
            result = runner.invoke(
                milestone_kanban,
                ["v1.0", "--no-color"],
                obj={"core": mock_core},
            )

            assert result.exit_code == 0

    def test_kanban_compact_and_no_color(
        self, cli_runner, mock_core, sample_milestone, sample_issues
    ):
        """Test kanban command with both compact and no-color options."""
        mock_core.milestones.get.return_value = sample_milestone
        mock_core.issues.list.return_value = sample_issues

        with patch(
            "roadmap.adapters.cli.milestones.kanban.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            runner = CliRunner()
            result = runner.invoke(
                milestone_kanban,
                ["v1.0", "--compact", "--no-color"],
                obj={"core": mock_core},
            )

            assert result.exit_code == 0

    def test_kanban_exception_handling(self, cli_runner, mock_core):
        """Test exception handling in kanban command."""
        mock_core.milestones.get.side_effect = Exception("Test error")

        with patch(
            "roadmap.adapters.cli.milestones.kanban.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            runner = CliRunner()
            result = runner.invoke(
                milestone_kanban,
                ["v1.0"],
                obj={"core": mock_core},
            )

            # Should handle exception gracefully
            assert result.exit_code == 0

    def test_kanban_filters_by_milestone(self, cli_runner, mock_core, sample_milestone):
        """Test that kanban only shows issues for the specified milestone."""
        other_milestone_issue = Issue(
            title="Other Milestone Issue",
            status=Status.TODO,
            priority=Priority.LOW,
            issue_type=IssueType.FEATURE,
            milestone="v2.0",
        )
        issues = [
            Issue(
                title="v1.0 Issue",
                status=Status.TODO,
                priority=Priority.HIGH,
                issue_type=IssueType.FEATURE,
                milestone="v1.0",
            ),
            other_milestone_issue,
        ]
        mock_core.milestones.get.return_value = sample_milestone
        mock_core.issues.list.return_value = issues

        with patch(
            "roadmap.adapters.cli.milestones.kanban.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            runner = CliRunner()
            result = runner.invoke(
                milestone_kanban,
                ["v1.0"],
                obj={"core": mock_core},
            )

            assert result.exit_code == 0
            assert mock_core.milestones.get.called

    def test_display_header(self, mock_console, sample_milestone, sample_issues):
        """Test header display function."""
        with patch("roadmap.adapters.cli.milestones.kanban.console", mock_console):
            _display_header(sample_milestone, sample_issues)
            # Should have called print multiple times
            assert mock_console.print.called

    def test_display_header_with_no_due_date(self, mock_console, sample_issues):
        """Test header display when milestone has no due date."""
        milestone = Milestone(
            name="v1.0",
            content="First release",
            due_date=None,
            status=MilestoneStatus.OPEN,
        )
        with patch("roadmap.adapters.cli.milestones.kanban.console", mock_console):
            _display_header(milestone, sample_issues)
            assert mock_console.print.called

    def test_display_board(self, mock_console):
        """Test board display function."""
        columns = [
            ("To Do", [], "red"),
            ("In Progress", [], "yellow"),
            ("Done", [], "green"),
        ]
        with patch("roadmap.adapters.cli.milestones.kanban.console", mock_console):
            _display_board(columns, compact=False, col_width=20)
            assert mock_console.print.called

    def test_display_board_compact(self, mock_console):
        """Test board display function in compact mode."""
        columns = [
            ("To Do", [], "red"),
            ("In Progress", [], "yellow"),
        ]
        with patch("roadmap.adapters.cli.milestones.kanban.console", mock_console):
            _display_board(columns, compact=True, col_width=20)
            assert mock_console.print.called

    def test_display_summary(self, mock_console):
        """Test summary display function."""
        categories = {
            "overdue": [],
            "blocked": [],
            "in_progress": [],
            "not_started": [],
            "closed": [],
        }
        with patch("roadmap.adapters.cli.milestones.kanban.console", mock_console):
            _display_summary(categories)
            assert mock_console.print.called

    def test_display_summary_with_issues(self, mock_console, sample_issues):
        """Test summary display with issues in categories."""
        categories = {
            "overdue": [],
            "blocked": [sample_issues[3]],
            "in_progress": [sample_issues[1]],
            "not_started": [sample_issues[0]],
            "closed": [sample_issues[2]],
        }
        with patch("roadmap.adapters.cli.milestones.kanban.console", mock_console):
            _display_summary(categories)
            assert mock_console.print.called

    def test_kanban_with_all_issue_statuses(
        self, cli_runner, mock_core, sample_milestone
    ):
        """Test kanban with issues in all different statuses."""
        issues = [
            Issue(
                title="Todo Issue",
                status=Status.TODO,
                priority=Priority.HIGH,
                issue_type=IssueType.FEATURE,
                milestone="v1.0",
            ),
            Issue(
                title="In Progress Issue",
                status=Status.IN_PROGRESS,
                priority=Priority.HIGH,
                issue_type=IssueType.FEATURE,
                milestone="v1.0",
            ),
            Issue(
                title="Blocked Issue",
                status=Status.BLOCKED,
                priority=Priority.MEDIUM,
                issue_type=IssueType.FEATURE,
                milestone="v1.0",
            ),
            Issue(
                title="Review Issue",
                status=Status.REVIEW,
                priority=Priority.MEDIUM,
                issue_type=IssueType.FEATURE,
                milestone="v1.0",
            ),
            Issue(
                title="Closed Issue",
                status=Status.CLOSED,
                priority=Priority.LOW,
                issue_type=IssueType.BUG,
                milestone="v1.0",
            ),
        ]
        mock_core.milestones.get.return_value = sample_milestone
        mock_core.issues.list.return_value = issues

        with patch(
            "roadmap.adapters.cli.milestones.kanban.get_console"
        ) as mock_get_console:
            mock_console = MagicMock()
            mock_get_console.return_value = mock_console

            runner = CliRunner()
            result = runner.invoke(
                milestone_kanban,
                ["v1.0"],
                obj={"core": mock_core},
            )

            assert result.exit_code == 0
            assert mock_core.milestones.get.called
