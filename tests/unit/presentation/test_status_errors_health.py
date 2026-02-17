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
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


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
                    assert (
                        "No such command" not in clean_cli_output(result.output)
                        or result.exit_code == 0
                    )


class TestStatusEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_status_with_zero_issues_multiple_milestones(self):
        """Should handle zero issues with multiple milestones."""
        runner = CliRunner()
        ctx_obj = {
            "core": MagicMock(),
        }

        with patch(
            "roadmap.adapters.cli.status.StatusSnapshotService.build_snapshot_tables"
        ) as mock_snapshot:
            mock_snapshot.return_value = {
                "entities": {
                    "columns": ["Type", "Open", "Closed", "Archived", "Total"],
                    "rows": [
                        ["Issues", 0, 0, 0, 0],
                        ["Milestones", 3, 0, 0, 3],
                        ["Projects", 0, 0, 0, 0],
                        ["Total", 3, 0, 0, 3],
                    ],
                }
            }
            with patch(
                "roadmap.adapters.cli.status._render_snapshot_tables"
            ) as mock_render:
                with runner.isolated_filesystem():
                    runner.invoke(
                        status,
                        [],
                        obj=ctx_obj,
                        catch_exceptions=False,
                    )
                mock_snapshot.assert_called_once_with(ctx_obj["core"])
                mock_render.assert_called_once()

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
