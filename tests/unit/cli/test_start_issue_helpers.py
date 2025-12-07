"""
Tests for start issue helpers.
"""

from datetime import datetime
from unittest.mock import Mock

from roadmap.adapters.cli.start_issue_helpers import (
    StartDateParser,
    StartIssueDisplay,
    StartIssueWorkflow,
)
from roadmap.core.domain import Status


class TestStartDateParser:
    """Test start date parsing."""

    def test_parse_none_returns_now(self):
        """Parse None should return current datetime."""
        result = StartDateParser.parse_start_date(None)
        assert result is not None
        assert isinstance(result, datetime)
        # Check it's recent (within last 5 seconds)
        assert (datetime.now() - result).total_seconds() < 5

    def test_parse_empty_string_returns_now(self):
        """Parse empty string should return current datetime."""
        result = StartDateParser.parse_start_date("")
        assert result is not None
        assert isinstance(result, datetime)
        assert (datetime.now() - result).total_seconds() < 5

    def test_parse_date_only_format(self):
        """Parse YYYY-MM-DD format successfully."""
        result = StartDateParser.parse_start_date("2024-01-15")
        assert result == datetime(2024, 1, 15)

    def test_parse_datetime_format(self):
        """Parse YYYY-MM-DD HH:MM format successfully."""
        result = StartDateParser.parse_start_date("2024-01-15 14:30")
        assert result == datetime(2024, 1, 15, 14, 30)

    def test_parse_invalid_format_returns_none(self):
        """Parse invalid date format should return None."""
        result = StartDateParser.parse_start_date("not-a-date")
        assert result is None

    def test_parse_partial_date_returns_none(self):
        """Parse partial date should return None."""
        result = StartDateParser.parse_start_date("2024-01")
        assert result is None


class TestStartIssueWorkflow:
    """Test start issue workflow orchestration."""

    def test_start_work_updates_issue(self):
        """start_work should call core.issues.update with correct parameters."""
        mock_core = Mock()
        mock_core.issues = Mock()
        mock_issue = Mock()
        mock_core.issues.update.return_value = mock_issue

        issue_id = "ISS-123"
        start_date = datetime(2024, 1, 15, 10, 30)

        result = StartIssueWorkflow.start_work(mock_core, issue_id, start_date)

        mock_core.issues.update.assert_called_once_with(
            issue_id,
            actual_start_date=start_date,
            status=Status.IN_PROGRESS,
            progress_percentage=0.0,
        )
        assert result == mock_issue

    def test_start_work_returns_none_on_failure(self):
        """start_work should return None when update fails."""
        mock_core = Mock()
        mock_core.issues = Mock()
        mock_core.issues.update.return_value = None

        result = StartIssueWorkflow.start_work(mock_core, "ISS-123", datetime.now())

        assert result is None

    def test_should_create_branch_true_when_flag_set(self):
        """should_create_branch returns True when git_branch_flag is True."""
        mock_core = Mock()
        result = StartIssueWorkflow.should_create_branch(True, mock_core)
        assert result is True

    def test_should_create_branch_false_when_flag_false(self):
        """should_create_branch returns False when git_branch_flag is False.

        Note: Config checking code tries to import non-existent RoadmapConfig,
        so it always falls through to the except block returning False.
        """
        mock_core = Mock()
        result = StartIssueWorkflow.should_create_branch(False, mock_core)
        assert result is False


class TestStartIssueDisplay:
    """Test start issue display helpers."""

    def test_show_started_displays_issue_info(self):
        """show_started should display issue title and start date."""
        mock_console = Mock()
        mock_issue = Mock()
        mock_issue.title = "Test Issue"
        start_date = datetime(2024, 1, 15, 14, 30)

        StartIssueDisplay.show_started(mock_issue, start_date, mock_console)

        assert mock_console.print.call_count == 3
        calls = mock_console.print.call_args_list

        # Check for issue title
        assert "Test Issue" in calls[0][0][0]
        assert "🚀 Started work on:" in calls[0][0][0]

        # Check for start date
        assert "2024-01-15 14:30" in calls[1][0][0]

        # Check for status
        assert "Status: In Progress" in calls[2][0][0]

    def test_show_branch_created_without_checkout(self):
        """show_branch_created should display branch name without checkout message."""
        mock_console = Mock()
        branch_name = "feature/ISS-123"

        StartIssueDisplay.show_branch_created(branch_name, False, mock_console)

        assert mock_console.print.call_count == 1
        call_text = mock_console.print.call_args[0][0]
        assert "feature/ISS-123" in call_text
        assert "🌿 Created Git branch:" in call_text

    def test_show_branch_created_with_checkout(self):
        """show_branch_created should display branch name and checkout message."""
        mock_console = Mock()
        branch_name = "feature/ISS-123"

        StartIssueDisplay.show_branch_created(branch_name, True, mock_console)

        assert mock_console.print.call_count == 2
        calls = mock_console.print.call_args_list

        # Check for branch creation
        assert "feature/ISS-123" in calls[0][0][0]
        assert "🌿 Created Git branch:" in calls[0][0][0]

        # Check for checkout message
        assert "feature/ISS-123" in calls[1][0][0]
        assert "✅ Checked out branch:" in calls[1][0][0]

    def test_show_branch_warning_with_uncommitted_changes(self):
        """show_branch_warning should display uncommitted changes warning."""
        mock_console = Mock()
        mock_core = Mock()
        mock_core.git._run_git_command.return_value = "M  some_file.py\n"

        StartIssueDisplay.show_branch_warning(mock_core, mock_console)

        mock_console.print.assert_called_once()
        warning_text = mock_console.print.call_args[0][0]
        assert "uncommitted changes" in warning_text
        assert "⚠️" in warning_text

    def test_show_branch_warning_with_clean_tree(self):
        """show_branch_warning should display generic warning for clean tree."""
        mock_console = Mock()
        mock_core = Mock()
        mock_core.git._run_git_command.return_value = ""

        StartIssueDisplay.show_branch_warning(mock_core, mock_console)

        mock_console.print.assert_called_once()
        warning_text = mock_console.print.call_args[0][0]
        assert "Failed to create or checkout branch" in warning_text
        assert "⚠️" in warning_text

    def test_show_branch_warning_with_none_status(self):
        """show_branch_warning should handle None status output."""
        mock_console = Mock()
        mock_core = Mock()
        mock_core.git._run_git_command.return_value = None

        StartIssueDisplay.show_branch_warning(mock_core, mock_console)

        mock_console.print.assert_called_once()
        warning_text = mock_console.print.call_args[0][0]
        assert "Failed to create or checkout branch" in warning_text

    def test_show_branch_warning_on_git_exception(self):
        """show_branch_warning should handle git command exceptions."""
        mock_console = Mock()
        mock_core = Mock()
        mock_core.git._run_git_command.side_effect = Exception("Git error")

        StartIssueDisplay.show_branch_warning(mock_core, mock_console)

        mock_console.print.assert_called_once()
        warning_text = mock_console.print.call_args[0][0]
        assert "Failed to create or checkout branch" in warning_text
        assert "⚠️" in warning_text
