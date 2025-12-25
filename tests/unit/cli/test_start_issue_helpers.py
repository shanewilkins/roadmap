"""
Tests for start issue helpers.
"""

from datetime import datetime
from unittest.mock import Mock

from roadmap.core.domain import Status
from roadmap.core.services import StartIssueService
from tests.unit.domain.test_data_factory import TestDataFactory


class TestStartDateParser:
    """Test start date parsing."""

    def test_parse_none_returns_now(self):
        """Parse None should return current datetime."""
        service = StartIssueService(None)
        result = service.parse_start_date(None)
        assert result is not None
        assert isinstance(result, datetime)
        # Check it's recent (within last 5 seconds)
        assert (datetime.now() - result).total_seconds() < 5

    def test_parse_empty_string_returns_now(self):
        """Parse empty string should return current datetime."""
        service = StartIssueService(None)
        result = service.parse_start_date("")
        assert result is not None
        assert isinstance(result, datetime)
        assert (datetime.now() - result).total_seconds() < 5

    def test_parse_date_only_format(self):
        """Parse YYYY-MM-DD format successfully."""
        service = StartIssueService(None)
        result = service.parse_start_date("2024-01-15")
        assert result == datetime(2024, 1, 15)

    def test_parse_datetime_format(self):
        """Parse YYYY-MM-DD HH:MM format successfully."""
        service = StartIssueService(None)
        result = service.parse_start_date("2024-01-15 14:30")
        assert result == datetime(2024, 1, 15, 14, 30)

    def test_parse_invalid_format_raises_error(self):
        """Parse invalid date format should raise ValueError."""
        service = StartIssueService(None)
        try:
            service.parse_start_date("not-a-date")
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Invalid date format" in str(e)

    def test_parse_partial_date_raises_error(self):
        """Parse partial date should raise ValueError."""
        service = StartIssueService(None)
        try:
            service.parse_start_date("2024-01")
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Invalid date format" in str(e)


class TestStartIssueWorkflow:
    """Test start issue workflow orchestration."""

    def test_start_work_updates_issue(self):
        """start_work should call core.issues.update with correct parameters."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues = Mock()
        mock_issue = TestDataFactory.create_mock_issue(status="open", priority="medium")
        mock_core.issues.update.return_value = mock_issue
        service = StartIssueService(mock_core)

        issue_id = "ISS-123"
        start_date = datetime(2024, 1, 15, 10, 30)

        result = service.start_work(issue_id, start_date)

        mock_core.issues.update.assert_called_once_with(
            issue_id,
            actual_start_date=start_date,
            status=Status.IN_PROGRESS,
            progress_percentage=0.0,
        )
        assert result == mock_issue

    def test_start_work_returns_none_on_failure(self):
        """start_work should return None when update fails."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues = Mock()
        mock_core.issues.update.return_value = None
        service = StartIssueService(mock_core)

        result = service.start_work("ISS-123", datetime.now())

        assert result is None

    def test_should_create_branch_true_when_flag_set(self):
        """should_create_branch returns True when git_branch_flag is True."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        result = StartIssueService(mock_core).should_create_branch(True)
        assert result

    def test_should_create_branch_false_when_flag_false(self):
        """should_create_branch returns False when git_branch_flag is False.

        Note: Config checking code tries to import non-existent RoadmapConfig,
        so it always falls through to the except block returning False.
        """
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        result = StartIssueService(mock_core).should_create_branch(False)
        assert not result


class TestStartIssueDisplay:
    """Test start issue display helpers."""

    def test_show_started_displays_issue_info(self):
        """show_started should display issue title and start date."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_console = Mock()
        service = StartIssueService(mock_core)
        service._console = mock_console
        mock_issue = TestDataFactory.create_mock_issue(status="open", priority="medium")
        mock_issue.title = "Test Issue"
        start_date = datetime(2024, 1, 15, 14, 30)

        service.display_started(mock_issue, start_date)

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
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_console = Mock()
        service = StartIssueService(mock_core)
        service._console = mock_console
        branch_name = "feature/ISS-123"

        service.display_branch_created(branch_name, False)

        assert mock_console.print.call_count == 1
        call_text = mock_console.print.call_args[0][0]
        assert "feature/ISS-123" in call_text
        assert "🌿 Created Git branch:" in call_text

    def test_show_branch_created_with_checkout(self):
        """show_branch_created should display branch name and checkout message."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_console = Mock()
        service = StartIssueService(mock_core)
        service._console = mock_console
        branch_name = "feature/ISS-123"

        service.display_branch_created(branch_name, True)

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
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.git._run_git_command.return_value = "M  some_file.py\n"
        mock_console = Mock()
        service = StartIssueService(mock_core)
        service._console = mock_console

        service.display_branch_warning()

        mock_console.print.assert_called_once()
        warning_text = mock_console.print.call_args[0][0]
        assert "uncommitted changes" in warning_text
        assert "⚠️" in warning_text

    def test_show_branch_warning_with_clean_tree(self):
        """show_branch_warning should display generic warning for clean tree."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.git._run_git_command.return_value = ""
        mock_console = Mock()
        service = StartIssueService(mock_core)
        service._console = mock_console

        service.display_branch_warning()

        mock_console.print.assert_called_once()
        warning_text = mock_console.print.call_args[0][0]
        assert "Failed to create or checkout branch" in warning_text
        assert "⚠️" in warning_text

    def test_show_branch_warning_with_none_status(self):
        """show_branch_warning should handle None status output."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.git._run_git_command.return_value = None
        mock_console = Mock()
        service = StartIssueService(mock_core)
        service._console = mock_console

        service.display_branch_warning()

        mock_console.print.assert_called_once()
        warning_text = mock_console.print.call_args[0][0]
        assert "Failed to create or checkout branch" in warning_text

    def test_show_branch_warning_on_git_exception(self):
        """show_branch_warning should handle git command exceptions."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.git._run_git_command.side_effect = Exception("Git error")
        mock_console = Mock()
        service = StartIssueService(mock_core)
        service._console = mock_console

        service.display_branch_warning()

        mock_console.print.assert_called_once()
        warning_text = mock_console.print.call_args[0][0]
        assert "Failed to create or checkout branch" in warning_text
        assert "⚠️" in warning_text
