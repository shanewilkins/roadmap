"""Error path tests for status.py CLI commands.

Tests cover error handling, data validation, and edge cases for status display.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.status import (
    _determine_overall_health,
    _display_check_result,
    _extract_check_status,
    _get_status_display_info,
    check_health,
    health,
    status,
)
from roadmap.core.domain.health import HealthStatus


class TestExtractCheckStatus:
    """Test _extract_check_status function."""

    def test_extract_tuple_format(self):
        """Tuple format should return as-is."""
        check_result = (HealthStatus.HEALTHY, "All good")
        status, message = _extract_check_status(check_result)

        assert status == HealthStatus.HEALTHY
        assert message == "All good"

    def test_extract_dict_format(self):
        """Dict format should extract status and message."""
        check_result = {"status": HealthStatus.DEGRADED, "message": "Warning"}
        status, message = _extract_check_status(check_result)

        assert status == HealthStatus.DEGRADED
        assert message == "Warning"

    def test_extract_dict_missing_status(self):
        """Dict without status should default to UNHEALTHY."""
        check_result = {"message": "Error"}
        status, message = _extract_check_status(check_result)

        assert status == HealthStatus.UNHEALTHY
        assert message == "Error"

    def test_extract_dict_missing_message(self):
        """Dict without message should default to empty string."""
        check_result = {"status": HealthStatus.HEALTHY}
        status, message = _extract_check_status(check_result)

        assert status == HealthStatus.HEALTHY
        assert message == ""

    def test_extract_dict_both_missing(self):
        """Dict without both status and message."""
        check_result = {}
        status, message = _extract_check_status(check_result)

        assert status == HealthStatus.UNHEALTHY
        assert message == ""

    def test_extract_none_result(self):
        """None result should be handled."""
        check_result = None
        with pytest.raises((TypeError, AttributeError)):
            _extract_check_status(check_result)


class TestGetStatusDisplayInfo:
    """Test _get_status_display_info function."""

    def test_healthy_status_display(self):
        """HEALTHY status should return correct icon and color."""
        icon, color = _get_status_display_info("HEALTHY")

        assert icon == "✅"
        assert color == "green"

    def test_degraded_status_display(self):
        """DEGRADED status should return correct icon and color."""
        icon, color = _get_status_display_info("DEGRADED")

        assert icon == "⚠️"
        assert color == "yellow"

    def test_unhealthy_status_display(self):
        """UNHEALTHY status should return correct icon and color."""
        icon, color = _get_status_display_info("UNHEALTHY")

        assert icon == "❌"
        assert color == "red"

    def test_unknown_status_display(self):
        """Unknown status should return default icon and color."""
        icon, color = _get_status_display_info("UNKNOWN")

        assert icon == "?"
        assert color == "white"

    def test_lowercase_status_display(self):
        """Lowercase status should not match."""
        icon, color = _get_status_display_info("healthy")

        assert icon == "?"
        assert color == "white"

    def test_empty_status_display(self):
        """Empty status should return default icon and color."""
        icon, color = _get_status_display_info("")

        assert icon == "?"
        assert color == "white"


class TestDisplayCheckResult:
    """Test _display_check_result function."""

    def test_display_with_message(self, capsys):
        """Should display check name, status, and message."""
        _display_check_result("database_check", "HEALTHY", "Connected")

        captured = capsys.readouterr()
        assert "Database Check" in captured.out
        assert "HEALTHY" in captured.out
        assert "Connected" in captured.out

    def test_display_without_message(self, capsys):
        """Should display check name and status without message."""
        _display_check_result("git_check", "UNHEALTHY", "")

        captured = capsys.readouterr()
        assert "Git Check" in captured.out
        assert "UNHEALTHY" in captured.out
        assert "  \n" not in captured.out  # No indented empty message

    def test_display_name_formatting(self, capsys):
        """Check name should be converted to title case."""
        _display_check_result("long_check_name", "DEGRADED", "Info")

        captured = capsys.readouterr()
        assert "Long Check Name" in captured.out

    def test_display_single_word_check(self, capsys):
        """Single word check name should be capitalized."""
        _display_check_result("storage", "HEALTHY", "OK")

        captured = capsys.readouterr()
        assert "Storage" in captured.out

    def test_display_with_multiline_message(self, capsys):
        """Multiline messages should be displayed."""
        _display_check_result("config", "UNHEALTHY", "Line 1\nLine 2")

        captured = capsys.readouterr()
        assert "Line 1\nLine 2" in captured.out


class TestDetermineOverallHealth:
    """Test _determine_overall_health function."""

    def test_all_healthy_checks(self):
        """All healthy checks should return HEALTHY."""
        checks = {
            "check1": (HealthStatus.HEALTHY, "OK"),
            "check2": (HealthStatus.HEALTHY, "OK"),
        }
        result = _determine_overall_health(checks)

        assert result == HealthStatus.HEALTHY

    def test_one_unhealthy_check(self):
        """Single unhealthy check should return UNHEALTHY."""
        checks = {
            "check1": (HealthStatus.HEALTHY, "OK"),
            "check2": (HealthStatus.UNHEALTHY, "Error"),
        }
        result = _determine_overall_health(checks)

        assert result == HealthStatus.UNHEALTHY

    def test_multiple_unhealthy_checks(self):
        """Multiple unhealthy checks should return UNHEALTHY."""
        checks = {
            "check1": (HealthStatus.UNHEALTHY, "Error1"),
            "check2": (HealthStatus.UNHEALTHY, "Error2"),
        }
        result = _determine_overall_health(checks)

        assert result == HealthStatus.UNHEALTHY

    def test_degraded_with_healthy(self):
        """Degraded with healthy should return DEGRADED."""
        checks = {
            "check1": (HealthStatus.HEALTHY, "OK"),
            "check2": (HealthStatus.DEGRADED, "Warning"),
        }
        result = _determine_overall_health(checks)

        assert result == HealthStatus.DEGRADED

    def test_degraded_superseded_by_unhealthy(self):
        """Unhealthy should override DEGRADED."""
        checks = {
            "check1": (HealthStatus.DEGRADED, "Warning"),
            "check2": (HealthStatus.UNHEALTHY, "Error"),
        }
        result = _determine_overall_health(checks)

        assert result == HealthStatus.UNHEALTHY

    def test_multiple_degraded_checks(self):
        """Multiple degraded checks should return DEGRADED."""
        checks = {
            "check1": (HealthStatus.DEGRADED, "Warning1"),
            "check2": (HealthStatus.DEGRADED, "Warning2"),
        }
        result = _determine_overall_health(checks)

        assert result == HealthStatus.DEGRADED

    def test_empty_checks_dict(self):
        """Empty checks dict should return HEALTHY."""
        checks = {}
        result = _determine_overall_health(checks)

        assert result == HealthStatus.HEALTHY

    def test_dict_format_checks(self):
        """Should handle dict format check results."""
        checks = {
            "check1": {"status": HealthStatus.HEALTHY, "message": "OK"},
            "check2": {"status": HealthStatus.UNHEALTHY, "message": "Error"},
        }
        result = _determine_overall_health(checks)

        assert result == HealthStatus.UNHEALTHY

    def test_mixed_format_checks(self):
        """Should handle mixed tuple and dict format."""
        checks = {
            "check1": (HealthStatus.HEALTHY, "OK"),
            "check2": {"status": HealthStatus.DEGRADED, "message": "Warning"},
        }
        result = _determine_overall_health(checks)

        assert result == HealthStatus.DEGRADED


class TestStatusCommand:
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

    def test_health_with_check_subcommand(self):
        """Health check subcommand should work."""
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
                        ["check"],
                        obj=ctx_obj,
                        catch_exceptions=False,
                    )

                assert result.exit_code == 0


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

    def test_determine_health_with_string_status(self):
        """Should handle string status values."""
        checks = {
            "test": {
                "status": "HEALTHY",  # string instead of enum
                "message": "OK",
            },
        }
        # This should not raise, even with string status
        result = _determine_overall_health(checks)
        assert result == HealthStatus.HEALTHY

    def test_check_result_with_very_long_message(self):
        """Should handle very long check messages."""
        long_message = "x" * 1000
        checks = {
            "test": (HealthStatus.DEGRADED, long_message),
        }
        result = _determine_overall_health(checks)

        assert result == HealthStatus.DEGRADED

    def test_display_check_with_special_characters(self, capsys):
        """Should handle special characters in messages."""
        _display_check_result("test_check", "HEALTHY", "Status: ✓ OK → Success")

        captured = capsys.readouterr()
        assert "✓" in captured.out
        assert "→" in captured.out
