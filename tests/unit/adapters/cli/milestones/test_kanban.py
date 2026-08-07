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
from roadmap.core.domain import MilestoneStatus, Priority, Status
from roadmap.core.domain.issue import IssueType
from tests.factories import IssueBuilder, MilestoneBuilder


@pytest.fixture
def sample_milestone():
    """Create a sample milestone."""
    return (
        MilestoneBuilder()
        .with_name("v1-0")
        .with_content("First release")
        .with_due_date(datetime.now(UTC) + timedelta(days=30))
        .with_status(MilestoneStatus.OPEN)
        .build()
    )


@pytest.fixture
def sample_issues():
    """Create sample issues for kanban board."""
    return [
        IssueBuilder()
        .with_title("Feature A - To Do")
        .with_status(Status.TODO)
        .with_priority(Priority.HIGH)
        .with_type(IssueType.FEATURE)
        .with_milestone("v1-0")
        .build(),
        IssueBuilder()
        .with_title("Feature B - In Progress")
        .with_status(Status.IN_PROGRESS)
        .with_priority(Priority.MEDIUM)
        .with_type(IssueType.FEATURE)
        .with_milestone("v1-0")
        .build(),
        IssueBuilder()
        .with_title("Bug Fix - Closed")
        .with_status(Status.CLOSED)
        .with_priority(Priority.HIGH)
        .with_type(IssueType.BUG)
        .with_milestone("v1-0")
        .build(),
        IssueBuilder()
        .with_title("Task - Blocked")
        .with_status(Status.BLOCKED)
        .with_priority(Priority.MEDIUM)
        .with_type(IssueType.FEATURE)
        .with_milestone("v1-0")
        .build(),
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
                ["v1-0"],
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
                ["v1-0"],
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
                ["v1-0", "--compact"],
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
                ["v1-0", "--no-color"],
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
                ["v1-0", "--compact", "--no-color"],
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
                ["v1-0"],
                obj={"core": mock_core},
            )

            # Should handle exception gracefully
            assert result.exit_code == 0

    def test_kanban_filters_by_milestone(self, cli_runner, mock_core, sample_milestone):
        """Test that kanban only shows issues for the specified milestone."""
        other_milestone_issue = (
            IssueBuilder()
            .with_title("Other Milestone Issue")
            .with_status(Status.TODO)
            .with_priority(Priority.LOW)
            .with_type(IssueType.FEATURE)
            .with_milestone("v2-0")
            .build()
        )
        issues = [
            IssueBuilder()
            .with_title("v1.0 Issue")
            .with_status(Status.TODO)
            .with_priority(Priority.HIGH)
            .with_type(IssueType.FEATURE)
            .with_milestone("v1-0")
            .build(),
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
                ["v1-0"],
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
        milestone = (
            MilestoneBuilder()
            .with_name("v1-0")
            .with_content("First release")
            .with_due_date(None)
            .with_status(MilestoneStatus.OPEN)
            .build()
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
            IssueBuilder()
            .with_title("Todo Issue")
            .with_status(Status.TODO)
            .with_priority(Priority.HIGH)
            .with_type(IssueType.FEATURE)
            .with_milestone("v1-0")
            .build(),
            IssueBuilder()
            .with_title("In Progress Issue")
            .with_status(Status.IN_PROGRESS)
            .with_priority(Priority.HIGH)
            .with_type(IssueType.FEATURE)
            .with_milestone("v1-0")
            .build(),
            IssueBuilder()
            .with_title("Blocked Issue")
            .with_status(Status.BLOCKED)
            .with_priority(Priority.MEDIUM)
            .with_type(IssueType.FEATURE)
            .with_milestone("v1-0")
            .build(),
            IssueBuilder()
            .with_title("Review Issue")
            .with_status(Status.REVIEW)
            .with_priority(Priority.MEDIUM)
            .with_type(IssueType.FEATURE)
            .with_milestone("v1-0")
            .build(),
            IssueBuilder()
            .with_title("Closed Issue")
            .with_status(Status.CLOSED)
            .with_priority(Priority.LOW)
            .with_type(IssueType.BUG)
            .with_milestone("v1-0")
            .build(),
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
                ["v1-0"],
                obj={"core": mock_core},
            )

            assert result.exit_code == 0
            assert mock_core.milestones.get.called
