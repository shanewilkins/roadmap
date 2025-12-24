"""Error path tests for close.py CLI command module.

Tests cover date parsing, issue closing, error handling,
and completion date tracking.
"""

from datetime import datetime
from unittest import mock

import pytest
import click
from click.testing import CliRunner

from roadmap.adapters.cli.issues.close import close_issue, _parse_completion_date


class TestParseDateCompletion:
    """Test _parse_completion_date function."""

    def test_parse_date_with_time(self):
        """Test parsing date with time."""
        result = _parse_completion_date("2024-12-25 14:30")
        assert result is not None
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 25
        assert result.hour == 14
        assert result.minute == 30

    def test_parse_date_without_time(self):
        """Test parsing date without time."""
        result = _parse_completion_date("2024-12-25")
        assert result is not None
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 25

    def test_parse_date_empty_string(self):
        """Test parsing empty string."""
        result = _parse_completion_date("")
        assert result is None

    def test_parse_date_none(self):
        """Test parsing None value."""
        result = _parse_completion_date(None)  # type: ignore
        assert result is None

    def test_parse_date_invalid_format(self):
        """Test parsing invalid date format."""
        result = _parse_completion_date("25-12-2024")
        assert result is None

    def test_parse_date_invalid_values(self):
        """Test parsing invalid date values."""
        result = _parse_completion_date("2024-13-01")  # Invalid month
        assert result is None

    def test_parse_date_leap_year(self):
        """Test parsing leap year date."""
        result = _parse_completion_date("2024-02-29")
        assert result is not None

    def test_parse_date_non_leap_year(self):
        """Test parsing non-leap year date."""
        result = _parse_completion_date("2023-02-29")
        assert result is None

    def test_parse_date_future_date(self):
        """Test parsing future date."""
        result = _parse_completion_date("2099-12-31 23:59")
        assert result is not None

    def test_parse_date_past_date(self):
        """Test parsing past date."""
        result = _parse_completion_date("1990-01-01 00:00")
        assert result is not None

    def test_parse_date_with_invalid_time(self):
        """Test parsing date with invalid time."""
        result = _parse_completion_date("2024-12-25 25:00")
        assert result is None

    def test_parse_date_midnight(self):
        """Test parsing midnight time."""
        result = _parse_completion_date("2024-12-25 00:00")
        assert result is not None

    def test_parse_date_whitespace(self):
        """Test parsing date with extra whitespace."""
        result = _parse_completion_date("  2024-12-25  ")
        # Should fail due to extra spaces
        assert result is None


class TestCloseIssueCommand:
    """Test close_issue command."""

    def test_close_issue_basic(self):
        """Test basic close issue command."""
        runner = CliRunner()
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Test Issue"
        mock_issue.actual_start_date = None
        mock_core.issues.update.return_value = mock_issue

        with mock.patch(
            "roadmap.adapters.cli.issues.close.require_initialized"
        ) as mock_require:
            mock_require.return_value = lambda f: f

            with runner.isolated_filesystem():
                # Create context with mock core
                ctx = click.Context(close_issue)
                ctx.obj = {"core": mock_core}

                with mock.patch(
                    "roadmap.adapters.cli.helpers.ensure_entity_exists"
                ) as mock_ensure:
                    mock_ensure.return_value = mock_issue

                    with mock.patch(
                        "roadmap.adapters.cli.issues.close.console"
                    ):
                        # Invoke command
                        result = runner.invoke(
                            close_issue,
                            ["ISSUE-1"],
                            obj={"core": mock_core},
                        )

    def test_close_issue_with_reason(self):
        """Test close issue with reason."""
        runner = CliRunner()
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Test Issue"
        mock_issue.actual_start_date = None
        mock_core.issues.update.return_value = mock_issue

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch(
                "roadmap.adapters.cli.issues.close.console"
            ):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--reason", "Fixed in release"],
                    obj={"core": mock_core},
                )

    def test_close_issue_with_date(self):
        """Test close issue with completion date."""
        runner = CliRunner()
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Test Issue"
        mock_issue.actual_start_date = datetime(2024, 12, 20, 10, 0)
        mock_issue.estimated_hours = 5.0
        mock_core.issues.update.return_value = mock_issue

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch(
                "roadmap.adapters.cli.issues.close.console"
            ):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time", "--date", "2024-12-25 14:30"],
                    obj={"core": mock_core},
                )

    def test_close_issue_with_invalid_date(self):
        """Test close issue with invalid date."""
        runner = CliRunner()
        mock_core = mock.MagicMock()

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ):
            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time", "--date", "invalid-date"],
                    obj={"core": mock_core},
                )

    def test_close_issue_record_time_current(self):
        """Test close issue recording current time."""
        runner = CliRunner()
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Test Issue"
        mock_issue.actual_start_date = datetime(2024, 12, 20, 10, 0)
        mock_issue.estimated_hours = 5.0
        mock_core.issues.update.return_value = mock_issue

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time"],
                    obj={"core": mock_core},
                )


class TestCloseIssueErrors:
    """Test error handling in close issue command."""

    def test_close_issue_not_found(self):
        """Test closing non-existent issue."""
        runner = CliRunner()
        mock_core = mock.MagicMock()

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.side_effect = click.Abort()

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                with pytest.raises(click.Abort):
                    runner.invoke(
                        close_issue,
                        ["INVALID"],
                        obj={"core": mock_core},
                    )

    def test_close_issue_update_fails(self):
        """Test when issue update fails."""
        runner = CliRunner()
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_core.issues.update.return_value = None  # Update failed

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1"],
                    obj={"core": mock_core},
                )


class TestCloseIssueDurationCalculation:
    """Test duration calculation when closing with dates."""

    def test_duration_on_target(self):
        """Test duration calculation when on target."""
        runner = CliRunner()
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Task"
        mock_issue.actual_start_date = datetime(2024, 12, 25, 10, 0)
        mock_issue.estimated_hours = 4.0
        mock_core.issues.update.return_value = mock_issue

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time", "--date", "2024-12-25 14:00"],
                    obj={"core": mock_core},
                )

    def test_duration_over_estimate(self):
        """Test duration calculation when over estimate."""
        runner = CliRunner()
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Task"
        mock_issue.actual_start_date = datetime(2024, 12, 25, 10, 0)
        mock_issue.estimated_hours = 3.0  # Estimate 3 hours
        mock_core.issues.update.return_value = mock_issue

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time", "--date", "2024-12-25 15:00"],
                    obj={"core": mock_core},
                )

    def test_duration_under_estimate(self):
        """Test duration calculation when under estimate."""
        runner = CliRunner()
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Task"
        mock_issue.actual_start_date = datetime(2024, 12, 25, 10, 0)
        mock_issue.estimated_hours = 5.0  # Estimate 5 hours
        mock_core.issues.update.return_value = mock_issue

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time", "--date", "2024-12-25 12:00"],
                    obj={"core": mock_core},
                )

    def test_no_start_date(self):
        """Test when issue has no start date."""
        runner = CliRunner()
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Task"
        mock_issue.actual_start_date = None
        mock_issue.estimated_hours = 5.0
        mock_core.issues.update.return_value = mock_issue

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time", "--date", "2024-12-25 14:30"],
                    obj={"core": mock_core},
                )
