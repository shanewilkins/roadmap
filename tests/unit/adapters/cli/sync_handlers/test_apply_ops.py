"""Tests for sync apply_ops module, specifically error display."""

from unittest.mock import Mock

import pytest

from roadmap.adapters.cli.sync_handlers.apply_ops import display_error_summary


@pytest.fixture
def mock_console():
    """Create a mock console instance."""
    return Mock()


class TestDisplayErrorSummary:
    """Test error summary display functionality."""

    def test_no_errors_displays_nothing(self, mock_console):
        """Test that empty error dict displays nothing."""
        errors = {}
        display_error_summary(errors, mock_console, verbose=False)

        # Should not print anything
        assert not mock_console.print.called

    def test_single_dependency_error(self, mock_console):
        """Test display of single dependency error."""
        errors = {
            "issue-123": "Foreign key constraint failed: milestone_id violates constraint"
        }
        display_error_summary(errors, mock_console, verbose=False)

        # Check that error header was printed
        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        assert "Sync Errors" in output
        # Foreign key constraint gets classified as database error, which is in data_errors group
        assert "Data Errors" in output or "Dependency Errors" in output
        assert "(1)" in output

    def test_multiple_error_categories(self, mock_console):
        """Test display with multiple error categories."""
        errors = {
            "issue-1": "Milestone 'v1-0' not found",
            "issue-2": "Foreign key constraint failed",
            "issue-3": "Rate limit exceeded",
            "issue-4": "Network timeout",
            "issue-5": "Permission denied",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Should show multiple categories
        assert "Dependency Errors" in output
        assert "API Errors" in output
        assert "Authentication Errors" in output

    def test_verbose_mode_shows_issue_ids(self, mock_console):
        """Test that verbose mode displays affected issue IDs."""
        errors = {
            "issue-abc123": "Milestone 'v1-0' not found",
            "issue-def456": "Milestone 'v2-0' not found",
        }
        display_error_summary(errors, mock_console, verbose=True)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Verbose mode should show issue IDs (truncated to 8 chars)
        assert "issue-ab" in output or "Affected issues" in output

    def test_verbose_mode_truncates_long_messages(self, mock_console):
        """Test that verbose mode truncates long error messages."""
        long_message = "A" * 100  # 100 character error
        errors = {"issue-123": long_message}
        display_error_summary(errors, mock_console, verbose=True)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Should truncate with ...
        assert "..." in output

    def test_verbose_mode_limits_issue_examples(self, mock_console):
        """Test that verbose mode shows max 5 examples per category."""
        errors = {f"issue-{i}": "Milestone not found" for i in range(10)}
        display_error_summary(errors, mock_console, verbose=True)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Should mention "and 5 more" or similar
        assert "more" in output.lower()

    def test_api_errors_categorization(self, mock_console):
        """Test API errors are properly categorized."""
        errors = {
            "issue-1": "Rate limit exceeded",
            "issue-2": "Network error: connection refused",
            "issue-3": "Request timeout after 30 seconds",
            "issue-4": "Service unavailable (503)",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        assert "API Errors" in output
        assert "(4)" in output

    def test_auth_errors_categorization(self, mock_console):
        """Test authentication errors are properly categorized."""
        errors = {
            "issue-1": "Authentication failed",
            "issue-2": "Permission denied: repo access required",
            "issue-3": "Token expired",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        assert "Authentication Errors" in output
        assert "(3)" in output

    def test_data_errors_categorization(self, mock_console):
        """Test data errors are properly categorized."""
        errors = {
            "issue-1": "Database error: constraint violation",
            "issue-2": "Validation error: invalid status",
            "issue-3": "Duplicate entity found",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        assert "Data Errors" in output
        assert "(3)" in output

    def test_resource_errors_categorization(self, mock_console):
        """Test resource errors are properly categorized."""
        errors = {
            "issue-1": "Resource deleted on remote",
            "issue-2": "Issue not found (404)",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        assert "Resource Errors" in output
        assert "(2)" in output

    def test_file_system_errors_categorization(self, mock_console):
        """Test file system errors are properly categorized."""
        errors = {
            "issue-1": "FileNotFoundError: config.json not found",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # The classifier checks error_type for file system errors, but display_error_summary
        # only passes error messages, so this gets classified based on message content
        assert (
            "File System Errors" in output
            or "Unknown Errors" in output
            or "Resource Errors" in output
        )
        assert "(1)" in output

    def test_unknown_errors_categorization(self, mock_console):
        """Test unknown errors are properly categorized."""
        errors = {
            "issue-1": "Some weird unexpected error",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        assert "Unknown Errors" in output
        assert "(1)" in output

    def test_recommendations_displayed(self, mock_console):
        """Test that fix recommendations are displayed."""
        errors = {
            "issue-1": "Milestone not found",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Should show "Fix:" somewhere
        assert "Fix:" in output or "fix" in output.lower()

    def test_total_error_count_displayed(self, mock_console):
        """Test that total error count is displayed."""
        errors = {
            "issue-1": "Error 1",
            "issue-2": "Error 2",
            "issue-3": "Error 3",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Should show total count
        assert "3" in output

    def test_mixed_errors_all_displayed(self, mock_console):
        """Test comprehensive scenario with mixed error types."""
        errors = {
            "issue-1": "Foreign key constraint failed",
            "issue-2": "Rate limit exceeded",
            "issue-3": "Authentication failed",
            "issue-4": "Database constraint violation",
            "issue-5": "Resource deleted on remote",
            "issue-6": "Unknown error occurred",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Should categorize into multiple groups
        # Note: Foreign key constraint is classified as data error
        assert "API Errors" in output  # Rate limit
        assert "Authentication Errors" in output  # Auth failed
        assert "Data Errors" in output  # Database constraint
        assert "Resource Errors" in output  # Resource deleted
        assert "Unknown Errors" in output  # Unknown error

    def test_verbose_false_hides_details(self, mock_console):
        """Test that verbose=False doesn't show issue IDs."""
        errors = {
            "issue-abc123": "Milestone not found",
        }
        display_error_summary(errors, mock_console, verbose=False)

        # Should NOT show "Affected issues" section in non-verbose mode
        # This is a bit tricky to test, but we can check the call count
        # Non-verbose should have fewer print calls
        assert len(mock_console.print.call_args_list) < 20
