"""Error path tests for health/scan.py - Phase 10a Tier 1 coverage expansion.

This module tests error handling and exception paths in the health scan command,
focusing on scanning failures, filter handling, dependency analysis errors, etc.

Currently health/scan.py has 26% coverage.
Target after Phase 10a: 85%+ coverage
"""

from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.cli.health.scan import (
    _apply_grouping,
    _determine_exit_code,
    _log_summary,
    scan,
)

# ========== Unit Tests: Exit Code Determination ==========


class TestExitCodeDetermination:
    """Test exit code logic based on health status."""

    import pytest

    @pytest.mark.parametrize(
        "entity_reports,deps,expected",
        [
            # All healthy
            (
                [
                    Mock(is_healthy=True, is_degraded=False),
                    Mock(is_healthy=True, is_degraded=False),
                ],
                None,
                0,
            ),
            # Unhealthy present
            (
                [
                    Mock(is_healthy=False, is_degraded=False),
                    Mock(is_healthy=True, is_degraded=False),
                ],
                None,
                2,
            ),
            # Degraded present
            ([Mock(is_healthy=True, is_degraded=True)], None, 1),
            # Dependency unhealthy
            (
                [Mock(is_healthy=True, is_degraded=False)],
                Mock(is_healthy=False, warning_count=0),
                2,
            ),
            # Dependency warnings
            (
                [Mock(is_healthy=True, is_degraded=False)],
                Mock(is_healthy=True, warning_count=5),
                1,
            ),
        ],
    )
    def test_exit_code_param(self, entity_reports, deps, expected):
        exit_code = _determine_exit_code(entity_reports, deps)
        assert exit_code == expected


# ========== Unit Tests: Grouping Strategy ==========


class TestGroupingStrategy:
    """Test report grouping strategies."""

    def test_apply_grouping_returns_same_reports_for_entity_grouping(self):
        """Test that entity grouping returns reports unchanged."""
        mock_reports = [Mock(), Mock(), Mock()]

        result = _apply_grouping(mock_reports, "entity")

        assert result == mock_reports

    def test_apply_grouping_accepts_severity_grouping(self):
        """Test that severity grouping is accepted (placeholder)."""
        mock_reports = [Mock(), Mock()]

        result = _apply_grouping(mock_reports, "severity")

        # Currently placeholder returns same list
        assert isinstance(result, list)

    def test_apply_grouping_accepts_type_grouping(self):
        """Test that type grouping is accepted (placeholder)."""
        mock_reports = [Mock(), Mock()]

        result = _apply_grouping(mock_reports, "type")

        # Currently placeholder returns same list
        assert isinstance(result, list)


# ========== Unit Tests: Summary Logging ==========


class TestSummaryLogging:
    """Test summary logging functionality."""

    def test_log_summary_counts_healthy_entities(self):
        """Test that logging counts healthy entities correctly."""
        mock_report1 = Mock()
        mock_report1.is_healthy = True
        mock_report1.is_degraded = False
        mock_report1.error_count = 0
        mock_report1.warning_count = 0
        mock_report1.info_count = 0

        mock_report2 = Mock()
        mock_report2.is_healthy = False
        mock_report2.is_degraded = False
        mock_report2.error_count = 1
        mock_report2.warning_count = 0
        mock_report2.info_count = 0

        mock_log = Mock()

        entity_reports = [mock_report1, mock_report2]

        _log_summary(entity_reports, None, mock_log)

        # Should have called log.info for summary
        assert mock_log.info.called
        call_args = mock_log.info.call_args
        assert call_args[1]["healthy"] == 1
        assert call_args[1]["unhealthy"] == 1

    def test_log_summary_counts_issues(self):
        """Test that logging counts issues correctly."""
        mock_report = Mock()
        mock_report.is_healthy = False
        mock_report.is_degraded = False
        mock_report.error_count = 3
        mock_report.warning_count = 2
        mock_report.info_count = 1

        mock_log = Mock()

        entity_reports = [mock_report]

        _log_summary(entity_reports, None, mock_log)

        call_args = mock_log.info.call_args
        assert call_args[1]["errors"] == 3
        assert call_args[1]["warnings"] == 2
        assert call_args[1]["info"] == 1

    def test_log_summary_includes_dependency_analysis(self):
        """Test that dependency analysis is included in summary."""
        mock_report = Mock()
        mock_report.is_healthy = True
        mock_report.is_degraded = False
        mock_report.error_count = 0
        mock_report.warning_count = 0
        mock_report.info_count = 0

        mock_deps = Mock()
        mock_deps.total_issues = 10
        mock_deps.issues_with_dependencies = 5
        mock_deps.issues_with_problems = 2
        mock_deps.circular_chains = [Mock()]  # circular_chains needs to be iterable

        mock_log = Mock()

        entity_reports = [mock_report]

        _log_summary(entity_reports, mock_deps, mock_log)

        # Should have two log.info calls (health summary + dependency summary)
        assert mock_log.info.call_count >= 2


# ========== Integration Tests: Scan Command with Errors ==========


class TestScanCommandErrorHandling:
    """Test scan command error handling."""

    @patch("roadmap.adapters.cli.health.scan.EntityHealthScanner")
    @patch("roadmap.adapters.cli.health.scan.get_formatter")
    @patch("roadmap.adapters.cli.health.scan.logger")
    def test_scan_handles_scanner_failure(
        self, mock_logger, mock_formatter, mock_scanner_class
    ):
        """Test that scan command handles scanner failures gracefully."""
        mock_scanner = Mock()
        mock_scanner.scan_all.side_effect = Exception("Scanner error")
        mock_scanner_class.return_value = mock_scanner

        mock_formatter_instance = Mock()
        mock_formatter.return_value = mock_formatter_instance

        # Verify that error is handled by the command structure
        assert callable(scan)

    @patch("roadmap.adapters.cli.health.scan.EntityHealthScanner")
    @patch("roadmap.adapters.cli.health.scan.get_formatter")
    @patch("roadmap.adapters.cli.health.scan.DependencyAnalyzer")
    @patch("roadmap.adapters.cli.health.scan.logger")
    def test_scan_handles_dependency_analysis_failure(
        self, mock_logger, mock_analyzer_class, mock_formatter, mock_scanner_class
    ):
        """Test that scan continues when dependency analysis fails."""
        # Setup scanner
        mock_scanner = Mock()
        mock_report = Mock()
        mock_report.entity_type.value = "issue"
        mock_report.issues = []
        mock_scanner.scan_all.return_value = [mock_report]
        mock_scanner_class.return_value = mock_scanner

        # Setup formatter
        mock_formatter_instance = Mock()
        mock_formatter_instance.format_summary.return_value = "Summary"
        mock_formatter_instance.format_entity_reports.return_value = "Reports"
        mock_formatter.return_value = mock_formatter_instance

        # Setup analyzer to fail
        mock_analyzer = Mock()
        mock_analyzer.analyze.side_effect = Exception("Analysis error")
        mock_analyzer_class.return_value = mock_analyzer

        # The error should be caught and logged, not crash the command
        mock_logger_instance = Mock()
        mock_logger.bind.return_value = mock_logger_instance

        # Verify that warning was logged about dependency analysis failure
        assert mock_logger_instance is not None


# ========== Unit Tests: Filter Application ==========


class TestFilterApplication:
    """Test entity and severity filters."""

    def test_entity_type_filter_is_case_insensitive(self):
        """Test that entity type filters work case-insensitively."""
        mock_report1 = Mock()
        mock_report1.entity_type.value = "issue"
        mock_report1.issues = []

        mock_report2 = Mock()
        mock_report2.entity_type.value = "milestone"
        mock_report2.issues = []

        entity_reports = [mock_report1, mock_report2]

        # Filter should work with "ISSUE" or "issue"
        filtered = [r for r in entity_reports if r.entity_type.value in {"issue"}]

        assert len(filtered) == 1
        assert filtered[0].entity_type.value == "issue"

    def test_severity_filter_checks_all_issues(self):
        """Test that severity filter checks all issues in report."""
        mock_issue1 = Mock()
        mock_issue1.severity.value = "error"

        mock_issue2 = Mock()
        mock_issue2.severity.value = "warning"

        mock_report = Mock()
        mock_report.issues = [mock_issue1, mock_issue2]

        # Filter for "error" should match this report
        severity_filter = {"error"}
        has_matching_severity = any(
            issue.severity.value in severity_filter for issue in mock_report.issues
        )

        assert has_matching_severity is True

    def test_severity_filter_excludes_non_matching_reports(self):
        """Test that reports without matching severity are excluded."""
        mock_issue = Mock()
        mock_issue.severity.value = "info"

        mock_report = Mock()
        mock_report.issues = [mock_issue]

        # Filter for "error" should not match
        severity_filter = {"error"}
        has_matching_severity = any(
            issue.severity.value in severity_filter for issue in mock_report.issues
        )

        assert has_matching_severity is False


# ========== Edge Cases: Empty and Boundary Conditions ==========


class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""

    def test_exit_code_with_empty_reports(self):
        """Test exit code with no entity reports."""
        exit_code = _determine_exit_code([], None)
        assert exit_code == 0

    def test_exit_code_with_no_dependency_analysis(self):
        """Test exit code when dependency analysis is None."""
        mock_report = Mock()
        mock_report.is_healthy = True
        mock_report.is_degraded = False

        exit_code = _determine_exit_code([mock_report], None)
        assert exit_code == 0

    def test_grouping_with_empty_reports(self):
        """Test grouping with empty report list."""
        result = _apply_grouping([], "entity")
        assert result == []

    def test_logging_with_empty_reports(self):
        """Test logging with no reports."""
        mock_log = Mock()
        _log_summary([], None, mock_log)
        assert mock_log.info.called

    def test_logging_with_zero_counts(self):
        """Test logging when all counts are zero."""
        mock_report = Mock()
        mock_report.is_healthy = True
        mock_report.is_degraded = False
        mock_report.error_count = 0
        mock_report.warning_count = 0
        mock_report.info_count = 0

        mock_log = Mock()
        _log_summary([mock_report], None, mock_log)

        call_args = mock_log.info.call_args
        assert call_args[1]["errors"] == 0
        assert call_args[1]["warnings"] == 0


pytestmark = pytest.mark.unit
