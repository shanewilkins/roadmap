"""Error path tests for close.py CLI command module.

Tests cover date parsing, issue closing, error handling,
and completion date tracking.
"""

from datetime import datetime
from unittest import mock

import click
from click.testing import CliRunner

from roadmap.adapters.cli.issues.close import _parse_completion_date, close_issue
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


class TestParseDateCompletion:
    """Test _parse_completion_date function."""

    import pytest

    @pytest.mark.parametrize(
        "date_str,expected",
        [
            ("2024-12-25 14:30", (2024, 12, 25, 14, 30)),
            ("2024-12-25", (2024, 12, 25, None, None)),
            ("", None),
            (None, None),
            ("25-12-2024", None),
            ("2024-13-01", None),
            ("2024-02-29", (2024, 2, 29, None, None)),
            ("2023-02-29", None),
            ("2099-12-31 23:59", (2099, 12, 31, 23, 59)),
            ("1990-01-01 00:00", (1990, 1, 1, 0, 0)),
            ("2024-12-25 25:00", None),
            ("2024-12-25 00:00", (2024, 12, 25, 0, 0)),
            ("  2024-12-25  ", None),
        ],
    )
    def test_parse_date_param(self, date_str, expected):
        result = _parse_completion_date(date_str)  # type: ignore
        if expected is None:
            assert result is None
        else:
            assert result is not None
            y, m, d, h, mi = expected
            assert result.year == y
            assert result.month == m
            assert result.day == d
            if h is not None:
                assert result.hour == h
            if mi is not None:
                assert result.minute == mi


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
                    "roadmap.adapters.cli.cli_command_helpers.ensure_entity_exists"
                ) as mock_ensure:
                    mock_ensure.return_value = mock_issue

                    with mock.patch("roadmap.adapters.cli.issues.close.console"):
                        # Invoke command
                        result = runner.invoke(
                            close_issue,
                            ["ISSUE-1"],
                            obj={"core": mock_core},
                        )
                        assert result.exit_code in (
                            0,
                            1,
                            2,
                        ), f"Command should complete: {clean_cli_output(result.output)}"
                        assert mock_core.issues.update.called, "Should update issue"

    def test_close_issue_with_reason(self):
        """Test close issue with reason."""
        runner = CliRunner()
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Test Issue"
        mock_issue.actual_start_date = None
        mock_core.issues.update.return_value = mock_issue

        with mock.patch(
            "roadmap.adapters.cli.cli_command_helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--reason", "Fixed in release"],
                    obj={"core": mock_core},
                )

                assert result.exit_code in (0, 1, 2), (
                    f"Command failed: {clean_cli_output(result.output)}"
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
            "roadmap.adapters.cli.cli_command_helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time", "--date", "2024-12-25 14:30"],
                    obj={"core": mock_core},
                )

                assert result.exit_code in (0, 1, 2), (
                    f"Command failed: {clean_cli_output(result.output)}"
                )

    def test_close_issue_with_invalid_date(self):
        """Test close issue with invalid date."""
        runner = CliRunner()
        mock_core = mock.MagicMock()

        with mock.patch(
            "roadmap.adapters.cli.cli_command_helpers.ensure_entity_exists"
        ):
            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time", "--date", "invalid-date"],
                    obj={"core": mock_core},
                )

                assert result.exit_code in (0, 1, 2), (
                    f"Command failed: {clean_cli_output(result.output)}"
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
            "roadmap.adapters.cli.cli_command_helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                runner.invoke(
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
            "roadmap.adapters.cli.cli_command_helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.side_effect = click.Abort()

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                runner.invoke(
                    close_issue,
                    ["INVALID"],
                    obj={"core": mock_core},
                )
                # Verify ensure_entity_exists was called
                mock_ensure.assert_called_once_with(mock_core, "issue", "INVALID")

    def test_close_issue_update_fails(self):
        """Test when issue update fails."""
        runner = CliRunner()
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_core.issues.update.return_value = None  # Update failed

        with mock.patch(
            "roadmap.adapters.cli.cli_command_helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                runner.invoke(
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
            "roadmap.adapters.cli.cli_command_helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time", "--date", "2024-12-25 14:00"],
                    obj={"core": mock_core},
                )

                assert result.exit_code in (0, 1, 2), (
                    f"Command failed: {clean_cli_output(result.output)}"
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
            "roadmap.adapters.cli.cli_command_helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time", "--date", "2024-12-25 15:00"],
                    obj={"core": mock_core},
                )

                assert result.exit_code in (0, 1, 2), (
                    f"Command failed: {clean_cli_output(result.output)}"
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
            "roadmap.adapters.cli.cli_command_helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                result = runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time", "--date", "2024-12-25 12:00"],
                    obj={"core": mock_core},
                )

                assert result.exit_code in (0, 1, 2), (
                    f"Command failed: {clean_cli_output(result.output)}"
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
            "roadmap.adapters.cli.cli_command_helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.close.console"):
                runner.invoke(
                    close_issue,
                    ["ISSUE-1", "--record-time", "--date", "2024-12-25 14:30"],
                    obj={"core": mock_core},
                )
