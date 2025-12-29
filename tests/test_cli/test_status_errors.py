"""Error path tests for status.py CLI commands.

Tests cover error handling, data validation, and edge cases for status display.
"""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from roadmap.adapters.cli.health.formatter import HealthCheckFormatter
from roadmap.adapters.cli.status import (
    check_health,
    health,
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


class TestCheckHealthCommand:
    """Test health check command error handling."""

    def test_check_health_all_healthy(self):
        """All healthy checks should pass."""
        runner = CliRunner()
        ctx_obj = {
            "core": MagicMock(),
        }

        mock_checks = {
            "database": (HealthStatus.HEALTHY, "Connected"),
            "storage": (HealthStatus.HEALTHY, "Available"),
        }

        with patch(
            "roadmap.adapters.cli.status.HealthCheck"
        ) as mock_health_check_class:
            mock_health_check = MagicMock()
            mock_health_check_class.return_value = mock_health_check
            mock_health_check.run_all_checks.return_value = mock_checks

            with runner.isolated_filesystem():
                result = runner.invoke(
                    check_health,
                    [],
                    obj=ctx_obj,
                    catch_exceptions=False,
                )

                assert result.exit_code == 0

    def test_check_health_with_failures(self):
        """Failed health checks should be reported."""
        runner = CliRunner()
        ctx_obj = {
            "core": MagicMock(),
        }

        mock_checks = {
            "database": (HealthStatus.UNHEALTHY, "Connection failed"),
        }

        with patch(
            "roadmap.adapters.cli.status.HealthCheck"
        ) as mock_health_check_class:
            mock_health_check = MagicMock()
            mock_health_check_class.return_value = mock_health_check
            mock_health_check.run_all_checks.return_value = mock_checks

            with patch(
                "roadmap.adapters.cli.status.CoreInitializationPresenter"
            ) as mock_presenter_class:
                mock_presenter = MagicMock()
                mock_presenter_class.return_value = mock_presenter

                with runner.isolated_filesystem():
                    result = runner.invoke(
                        check_health,
                        [],
                        obj=ctx_obj,
                        catch_exceptions=False,
                    )

                assert result.exit_code == 0

    def test_check_health_exception(self):
        """Exception during health check should show error."""
        runner = CliRunner()
        ctx_obj = {
            "core": MagicMock(),
        }

        with patch(
            "roadmap.adapters.cli.status.HealthCheck"
        ) as mock_health_check_class:
            mock_health_check = MagicMock()
            mock_health_check_class.return_value = mock_health_check
            mock_health_check.run_all_checks.side_effect = Exception("Check failed")

            with patch(
                "roadmap.adapters.cli.status.CoreInitializationPresenter"
            ) as mock_presenter_class:
                mock_presenter = MagicMock()
                mock_presenter_class.return_value = mock_presenter

                with runner.isolated_filesystem():
                    result = runner.invoke(
                        check_health,
                        [],
                        obj=ctx_obj,
                        catch_exceptions=False,
                    )

                assert result.exit_code == 0

    def test_check_health_verbose_flag(self):
        """Verbose flag should be handled."""
        runner = CliRunner()
        ctx_obj = {
            "core": MagicMock(),
        }

        mock_checks = {
            "test": (HealthStatus.HEALTHY, "OK"),
        }

        with patch(
            "roadmap.adapters.cli.status.HealthCheck"
        ) as mock_health_check_class:
            mock_health_check = MagicMock()
            mock_health_check_class.return_value = mock_health_check
            mock_health_check.run_all_checks.return_value = mock_checks

            with patch(
                "roadmap.adapters.cli.status.CoreInitializationPresenter"
            ) as mock_presenter_class:
                mock_presenter = MagicMock()
                mock_presenter_class.return_value = mock_presenter

                with runner.isolated_filesystem():
                    result = runner.invoke(
                        check_health,
                        ["--verbose"],
                        obj=ctx_obj,
                        catch_exceptions=False,
                    )

                assert result.exit_code == 0


class TestHealthGroup:
    """Test health group command."""

    def test_health_no_subcommand_invokes_check(self):
        """Health group without subcommand should invoke check_health."""
        runner = CliRunner()
        ctx_obj = {
            "core": MagicMock(),
        }

        mock_checks = {
            "test": (HealthStatus.HEALTHY, "OK"),
        }

        with patch(
            "roadmap.adapters.cli.status.HealthCheck"
        ) as mock_health_check_class:
            mock_health_check = MagicMock()
            mock_health_check_class.return_value = mock_health_check
            mock_health_check.run_all_checks.return_value = mock_checks

            with patch(
                "roadmap.adapters.cli.status.CoreInitializationPresenter"
            ) as mock_presenter_class:
                mock_presenter = MagicMock()
                mock_presenter_class.return_value = mock_presenter

                with runner.isolated_filesystem():
                    result = runner.invoke(
                        health,
                        [],
                        obj=ctx_obj,
                        catch_exceptions=False,
                    )

                assert result.exit_code == 0

    def test_health_with_scan_subcommand(self):
        """Health scan subcommand should work."""
        runner = CliRunner()
        ctx_obj = {
            "core": MagicMock(),
        }

        with patch("roadmap.adapters.cli.health.scan.EntityHealthScanner"):
            with patch("roadmap.adapters.cli.health.scan.get_formatter"):
                with runner.isolated_filesystem():
                    result = runner.invoke(
                        health,
                        ["scan"],
                        obj=ctx_obj,
                    )

                # Should not raise an error about unknown command
                assert "No such command" not in result.output or result.exit_code == 0


class TestStatusEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_status_with_zero_issues_multiple_milestones(self):
        """Should handle zero issues with multiple milestones."""
        runner = CliRunner()
        ctx_obj = {
            "core": MagicMock(),
        }

        status_data = {
            "has_data": True,
            "issue_count": 0,
            "milestone_count": 3,
            "issues": [],
            "milestones": [
                {"name": "M1", "status": "open"},
                {"name": "M2", "status": "open"},
                {"name": "M3", "status": "open"},
            ],
        }

        with patch(
            "roadmap.adapters.cli.status.StatusDataService.gather_status_data"
        ) as mock_gather:
            mock_gather.return_value = status_data

            with patch(
                "roadmap.adapters.cli.status.MilestoneProgressService.get_all_milestones_progress"
            ) as mock_milestone_progress:
                mock_milestone_progress.return_value = {}

                with patch(
                    "roadmap.adapters.cli.status.IssueStatisticsService.get_all_status_counts"
                ) as mock_issue_counts:
                    mock_issue_counts.return_value = {}

                    with patch(
                        "roadmap.adapters.cli.status.MilestoneProgressPresenter.show_all_milestones"
                    ) as mock_show_milestones:
                        with patch(
                            "roadmap.adapters.cli.status.IssueStatusPresenter.show_all_issue_statuses"
                        ):
                            with runner.isolated_filesystem():
                                runner.invoke(
                                    status,
                                    [],
                                    obj=ctx_obj,
                                    catch_exceptions=False,
                                )

                            mock_show_milestones.assert_called()

    def test_formatter_with_very_long_message(self):
        """Formatter should handle very long check messages."""
        formatter = HealthCheckFormatter()
        long_message = "x" * 1000
        checks = {
            "test": (HealthStatus.DEGRADED, long_message),
        }

        output = formatter.format_plain(checks, details=False)
        assert "x" * 100 in output

    def test_formatter_with_special_characters(self):
        """Formatter should handle special characters in messages."""
        formatter = HealthCheckFormatter()
        checks = {
            "test_check": (HealthStatus.HEALTHY, "Status: ✓ OK → Success"),
        }

        output = formatter.format_plain(checks, details=False)
        assert "✓" in output
        assert "→" in output
