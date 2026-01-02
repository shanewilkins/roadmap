"""Error path tests for status.py CLI commands.

Tests cover error handling, data validation, and edge cases for status display.
"""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from roadmap.adapters.cli.health.formatter import HealthCheckFormatter
from roadmap.adapters.cli.status import (
    status,
)
from roadmap.core.domain.health import HealthStatus


class TestHealthCheckFormatter:
    """Test HealthCheckFormatter class."""

    def test_formatter_plain_text_basic(self):
        """Formatter should produce plain text output."""
        formatter = HealthCheckFormatter()
        checks = {
            "database": (HealthStatus.HEALTHY, "Connected"),
            "storage": (HealthStatus.HEALTHY, "Available"),
        }

        output = formatter.format_plain(checks, details=False)

        assert "Database: HEALTHY" in output
        assert "Storage: HEALTHY" in output
        assert "✅" in output

    def test_formatter_plain_text_with_degraded(self):
        """Formatter should show degraded status."""
        formatter = HealthCheckFormatter()
        checks = {
            "database": (HealthStatus.DEGRADED, "Slow"),
        }

        output = formatter.format_plain(checks, details=False)

        assert "Database: DEGRADED" in output
        assert "⚠️" in output

    def test_formatter_plain_text_with_details(self):
        """Formatter should include details when requested."""
        formatter = HealthCheckFormatter()
        checks = {
            "duplicate_issues": (HealthStatus.DEGRADED, "Found duplicates"),
        }

        output = formatter.format_plain(checks, details=True)

        assert "Recommendations:" in output
        assert "Fix Commands:" in output

    def test_formatter_json_output(self):
        """Formatter should produce valid JSON."""
        import json

        formatter = HealthCheckFormatter()
        checks = {
            "database": (HealthStatus.HEALTHY, "Connected"),
        }

        output = formatter.format_json(checks, details=False, hierarchical=True)
        data = json.loads(output)

        assert "metadata" in data
        assert "checks" in data
        assert data["metadata"]["overall_status"] == "HEALTHY"

    def test_formatter_json_hierarchical_with_details(self):
        """Formatter should produce hierarchical JSON with details."""
        import json

        formatter = HealthCheckFormatter()
        checks = {
            "duplicate_issues": (HealthStatus.DEGRADED, "Found duplicates"),
            "database": (HealthStatus.HEALTHY, "Connected"),
        }

        output = formatter.format_json(checks, details=True, hierarchical=True)
        data = json.loads(output)

        assert "metadata" in data
        assert len(data["checks"]["degraded"]) == 1
        assert len(data["checks"]["healthy"]) == 1
        assert "next_steps" in data


class TestStatusCommand:
    """Test status command error handling."""

    import pytest

    @pytest.mark.parametrize(
        "mock_gather_return, mock_gather_side_effect, cli_args, presenter_patch, presenter_method, presenter_arg, expected_exit",
        [
            # No data, should call show_empty_state
            (
                {"has_data": False, "issue_count": 0, "milestone_count": 0},
                None,
                [],
                "roadmap.adapters.cli.status.RoadmapStatusPresenter.show_empty_state",
                "show_empty_state",
                None,
                None,
            ),
            # Exception, should call show_error
            (
                None,
                Exception("Database error"),
                [],
                "roadmap.adapters.cli.status.RoadmapStatusPresenter.show_error",
                "show_error",
                "Database error",
                None,
            ),
            # Verbose flag, should exit 0
            (
                {"has_data": False, "issue_count": 0, "milestone_count": 0},
                None,
                ["--verbose"],
                "roadmap.adapters.cli.status.RoadmapStatusPresenter.show_empty_state",
                None,
                None,
                0,
            ),
        ],
    )
    def test_status_param(
        self,
        mock_gather_return,
        mock_gather_side_effect,
        cli_args,
        presenter_patch,
        presenter_method,
        presenter_arg,
        expected_exit,
    ):
        runner = CliRunner()
        ctx_obj = {"core": MagicMock()}
        with patch(
            "roadmap.adapters.cli.status.StatusDataService.gather_status_data"
        ) as mock_gather:
            if mock_gather_side_effect:
                mock_gather.side_effect = mock_gather_side_effect
            else:
                mock_gather.return_value = mock_gather_return
            if presenter_patch:
                with patch(presenter_patch) as mock_presenter:
                    with runner.isolated_filesystem():
                        result = runner.invoke(
                            status, cli_args, obj=ctx_obj, catch_exceptions=False
                        )
                    if presenter_method:
                        if presenter_arg is not None:
                            mock_presenter.assert_called_once_with(presenter_arg)
                        else:
                            mock_presenter.assert_called_once()
                    if expected_exit is not None:
                        assert result.exit_code == expected_exit
            else:
                with runner.isolated_filesystem():
                    result = runner.invoke(
                        status, cli_args, obj=ctx_obj, catch_exceptions=False
                    )
                if expected_exit is not None:
                    assert result.exit_code == expected_exit

    """Test status command error handling."""

    def test_status_no_data(self):
        """Empty roadmap should show empty state."""
        runner = CliRunner()
        ctx_obj = {
            "core": MagicMock(),
        }

        with patch(
            "roadmap.adapters.cli.status.StatusDataService.gather_status_data"
        ) as mock_gather:
            mock_gather.return_value = {
                "has_data": False,
                "issue_count": 0,
                "milestone_count": 0,
            }

            with patch(
                "roadmap.adapters.cli.status.RoadmapStatusPresenter.show_empty_state"
            ) as mock_empty:
                with runner.isolated_filesystem():
                    runner.invoke(
                        status,
                        [],
                        obj=ctx_obj,
                        catch_exceptions=False,
                    )

                mock_empty.assert_called_once()

    def test_status_with_exception(self):
        """Exception during status gathering should show error."""
        runner = CliRunner()
        ctx_obj = {
            "core": MagicMock(),
        }

        with patch(
            "roadmap.adapters.cli.status.StatusDataService.gather_status_data"
        ) as mock_gather:
            mock_gather.side_effect = Exception("Database error")

            with patch(
                "roadmap.adapters.cli.status.RoadmapStatusPresenter.show_error"
            ) as mock_error:
                with runner.isolated_filesystem():
                    runner.invoke(
                        status,
                        [],
                        obj=ctx_obj,
                        catch_exceptions=False,
                    )

                mock_error.assert_called_once_with("Database error")

    def test_status_verbose_flag(self):
        """Verbose flag should be passed through."""
        runner = CliRunner()
        ctx_obj = {
            "core": MagicMock(),
        }

        with patch(
            "roadmap.adapters.cli.status.StatusDataService.gather_status_data"
        ) as mock_gather:
            mock_gather.return_value = {
                "has_data": False,
                "issue_count": 0,
                "milestone_count": 0,
            }

            with patch(
                "roadmap.adapters.cli.status.RoadmapStatusPresenter.show_empty_state"
            ):
                with runner.isolated_filesystem():
                    result = runner.invoke(
                        status,
                        ["--verbose"],
                        obj=ctx_obj,
                        catch_exceptions=False,
                    )

                assert result.exit_code == 0
