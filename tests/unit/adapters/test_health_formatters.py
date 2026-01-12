"""Tests for health output formatters."""

import json

import pytest

from roadmap.adapters.cli.health.formatters import (
    CSVFormatter,
    JSONFormatter,
    PlainTextFormatter,
    get_formatter,
)
from roadmap.core.services.utils.dependency_analyzer import (
    DependencyAnalysisResult,
    DependencyIssue,
    DependencyIssueType,
)
from roadmap.core.services.health.entity_health_scanner import (
    EntityHealthReport,
    EntityType,
    HealthIssue,
    HealthSeverity,
)


@pytest.fixture
def sample_report():
    """Create a sample entity health report."""
    return EntityHealthReport(
        entity_id="issue-1",
        entity_type=EntityType.ISSUE,
        entity_title="Test Issue",
        status="todo",
        issues=[
            HealthIssue(
                code="missing_description",
                message="Issue has no description",
                severity=HealthSeverity.WARNING,
                category="content",
            ),
        ],
    )


@pytest.fixture
def sample_dependency_result():
    """Create a sample dependency analysis result."""
    return DependencyAnalysisResult(
        total_issues=5,
        issues_with_dependencies=3,
        issues_with_problems=1,
        problems=[
            DependencyIssue(
                issue_id="issue-1",
                issue_type=DependencyIssueType.BROKEN,
                message="Depends on non-existent issue",
                affected_issues=["non-existent"],
            ),
        ],
        circular_chains=[],
    )


class TestPlainTextFormatter:
    """Test PlainTextFormatter."""

    def test_format_empty_reports(self):
        """Test formatting empty report list."""
        formatter = PlainTextFormatter()
        output = formatter.format_entity_reports([])

        assert "No entities" in output

    def test_format_single_report(self, sample_report):
        """Test formatting single entity report."""
        formatter = PlainTextFormatter()
        output = formatter.format_entity_reports([sample_report])

        assert "ISSUES (1)" in output
        assert "Test Issue" in output
        assert "issue-1" in output

    def test_format_multiple_reports(self, sample_report):
        """Test formatting multiple entity reports."""
        report2 = EntityHealthReport(
            entity_id="milestone-1",
            entity_type=EntityType.MILESTONE,
            entity_title="Test Milestone",
            status="in_progress",
            issues=[],
        )

        formatter = PlainTextFormatter()
        output = formatter.format_entity_reports([sample_report, report2])

        assert "ISSUES" in output
        assert "MILESTONES" in output

    def test_format_dependency_analysis(self, sample_dependency_result):
        """Test formatting dependency analysis."""
        formatter = PlainTextFormatter()
        output = formatter.format_dependency_analysis(sample_dependency_result)

        assert "DEPENDENCY ANALYSIS" in output
        assert "Total issues: 5" in output
        assert "broken_dependency" in output or "BROKEN" in output

    def test_format_summary(self, sample_report, sample_dependency_result):
        """Test formatting summary."""
        formatter = PlainTextFormatter()
        output = formatter.format_summary([sample_report], sample_dependency_result)

        assert "HEALTH SCAN SUMMARY" in output
        assert "Entities:" in output
        assert "Degraded:" in output

    def test_healthy_status_badge(self, sample_report):
        """Test status badge for healthy entity."""
        sample_report.issues = []
        formatter = PlainTextFormatter()
        output = formatter.format_entity_reports([sample_report])

        assert "✓" in output

    def test_degraded_status_badge(self, sample_report):
        """Test status badge for degraded entity."""
        formatter = PlainTextFormatter()
        output = formatter.format_entity_reports([sample_report])

        assert "⚠" in output


class TestJSONFormatter:
    """Test JSONFormatter."""

    def test_format_empty_reports(self):
        """Test formatting empty report list as JSON."""
        formatter = JSONFormatter()
        output = formatter.format_entity_reports([])

        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_format_single_report(self, sample_report):
        """Test formatting single report as JSON."""
        formatter = JSONFormatter()
        output = formatter.format_entity_reports([sample_report])

        data = json.loads(output)
        assert len(data) == 1
        assert data[0]["entity_id"] == "issue-1"
        assert data[0]["entity_type"] == "issue"
        assert data[0]["issue_count"] == 1

    def test_format_dependency_analysis(self, sample_dependency_result):
        """Test formatting dependency analysis as JSON."""
        formatter = JSONFormatter()
        output = formatter.format_dependency_analysis(sample_dependency_result)

        data = json.loads(output)
        assert data["total_issues"] == 5
        assert len(data["problems"]) == 1
        assert data["problems"][0]["issue_id"] == "issue-1"

    def test_format_summary(self, sample_report, sample_dependency_result):
        """Test formatting summary as JSON."""
        formatter = JSONFormatter()
        output = formatter.format_summary([sample_report], sample_dependency_result)

        data = json.loads(output)
        assert "summary" in data
        assert "entities" in data
        assert "dependencies" in data
        assert data["summary"]["total_entities"] == 1

    def test_json_is_valid(self, sample_report):
        """Ensure JSON output is valid."""
        formatter = JSONFormatter()
        output = formatter.format_entity_reports([sample_report])

        # Should not raise
        json.loads(output)


class TestCSVFormatter:
    """Test CSVFormatter."""

    def test_format_empty_reports(self):
        """Test formatting empty report list as CSV."""
        formatter = CSVFormatter()
        output = formatter.format_entity_reports([])

        lines = output.split("\n")
        # Should have header at least
        assert len(lines) >= 1
        assert "entity_id" in lines[0]

    def test_format_single_report(self, sample_report):
        """Test formatting single report as CSV."""
        formatter = CSVFormatter()
        output = formatter.format_entity_reports([sample_report])

        lines = output.split("\n")
        assert len(lines) >= 2  # header + 1 record
        assert "issue-1" in output
        assert "issue" in output
        assert "Test Issue" in output

    def test_csv_has_headers(self, sample_report):
        """Test CSV has proper headers."""
        formatter = CSVFormatter()
        output = formatter.format_entity_reports([sample_report])

        lines = output.split("\n")
        header = lines[0]
        assert "entity_id" in header
        assert "entity_type" in header
        assert "status" in header
        assert "is_healthy" in header

    def test_format_dependency_analysis(self, sample_dependency_result):
        """Test formatting dependency analysis as CSV."""
        formatter = CSVFormatter()
        output = formatter.format_dependency_analysis(sample_dependency_result)

        assert "issue_id" in output
        assert "issue_type" in output
        assert "issue-1" in output

    def test_format_summary(self, sample_report, sample_dependency_result):
        """Test formatting summary as CSV."""
        formatter = CSVFormatter()
        output = formatter.format_summary([sample_report], sample_dependency_result)

        # Should have metadata section
        assert "Health Scan Summary" in output or "metric,value" in output

    def test_csv_escaping(self):
        """Test proper CSV escaping for special characters."""
        report = EntityHealthReport(
            entity_id="issue-1",
            entity_type=EntityType.ISSUE,
            entity_title='Title with "quotes" and, commas',
            status="todo",
        )

        formatter = CSVFormatter()
        output = formatter.format_entity_reports([report])

        # Should handle escaping
        assert '"' in output or "Title with" in output


class TestFormatterFactory:
    """Test formatter factory function."""

    def test_get_plain_formatter(self):
        """Test getting plain text formatter."""
        formatter = get_formatter("plain")
        assert isinstance(formatter, PlainTextFormatter)

    def test_get_text_alias(self):
        """Test 'text' alias for plain text formatter."""
        formatter = get_formatter("text")
        assert isinstance(formatter, PlainTextFormatter)

    def test_get_json_formatter(self):
        """Test getting JSON formatter."""
        formatter = get_formatter("json")
        assert isinstance(formatter, JSONFormatter)

    def test_get_csv_formatter(self):
        """Test getting CSV formatter."""
        formatter = get_formatter("csv")
        assert isinstance(formatter, CSVFormatter)

    def test_case_insensitive(self):
        """Test case-insensitive formatter selection."""
        formatter1 = get_formatter("PLAIN")
        formatter2 = get_formatter("Plain")
        formatter3 = get_formatter("plain")

        assert isinstance(formatter1, PlainTextFormatter)
        assert isinstance(formatter2, PlainTextFormatter)
        assert isinstance(formatter3, PlainTextFormatter)

    def test_invalid_format(self):
        """Test error handling for invalid format."""
        with pytest.raises(ValueError) as exc_info:
            get_formatter("invalid")

        assert "Unknown format" in str(exc_info.value)


class TestFormatterConsistency:
    """Test consistency across formatters."""

    def test_all_formatters_handle_empty_reports(self):
        """Test all formatters handle empty reports."""
        formatters = [
            PlainTextFormatter(),
            JSONFormatter(),
            CSVFormatter(),
        ]

        for formatter in formatters:
            output = formatter.format_entity_reports([])
            assert isinstance(output, str)
            assert len(output) > 0

    def test_all_formatters_handle_summary(self, sample_report):
        """Test all formatters handle summary."""
        formatters = [
            PlainTextFormatter(),
            JSONFormatter(),
            CSVFormatter(),
        ]

        for formatter in formatters:
            output = formatter.format_summary([sample_report])
            assert isinstance(output, str)
            assert len(output) > 0
