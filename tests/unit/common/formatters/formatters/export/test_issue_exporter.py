"""Tests for issue exporter."""

import json
from unittest.mock import Mock, patch

import pytest

from roadmap.common.formatters.export.issue_exporter import IssueExporter
from roadmap.core.domain import Priority, Status


class MockIssue:
    """Mock issue for testing."""

    def __init__(
        self,
        issue_id="ISSUE-001",
        title="Test Issue",
        status=None,
        assignee="John",
        priority=None,
        estimated_hours=0,
        milestone="v1-0",
        created="2024-01-01",
        updated="2024-01-02",
        estimated_time_display="0h",
    ):
        """Initialize mock issue."""
        self.id = issue_id
        self.title = title
        self.status = status or Status.TODO
        self.assignee = assignee
        self.priority = priority or Priority.MEDIUM
        self.estimated_hours = estimated_hours
        self.milestone = milestone
        self.created = created
        self.updated = updated
        self.estimated_time_display = estimated_time_display


class TestIssueExporter:
    """Tests for IssueExporter class."""

    def test_export_json_format(self):
        """Test JSON export."""
        issues = [MockIssue()]

        with patch(
            "roadmap.common.formatters.export.issue_exporter.IssueTableFormatter.issues_to_table_data"
        ):
            with patch(
                "roadmap.common.formatters.export.issue_exporter.OutputFormatter"
            ) as mock_formatter:
                mock_formatter_instance = Mock()
                mock_formatter_instance.to_json.return_value = '{"test": "data"}'
                mock_formatter.return_value = mock_formatter_instance

                result = IssueExporter.export(issues, "json")  # type: ignore

                assert result == '{"test": "data"}'
                mock_formatter_instance.to_json.assert_called_once()

    def test_export_csv_format(self):
        """Test CSV export."""
        issues = [MockIssue()]

        with patch(
            "roadmap.common.formatters.export.issue_exporter.IssueTableFormatter.issues_to_table_data"
        ):
            with patch(
                "roadmap.common.formatters.export.issue_exporter.OutputFormatter"
            ) as mock_formatter:
                mock_formatter_instance = Mock()
                mock_formatter_instance.to_csv.return_value = "id,title\nISSUE-001,Test"
                mock_formatter.return_value = mock_formatter_instance

                result = IssueExporter.export(issues, "csv")  # type: ignore

                assert "id,title" in result

    def test_export_markdown_format(self):
        """Test Markdown export."""
        issues = [MockIssue()]

        with patch(
            "roadmap.common.formatters.export.issue_exporter.IssueTableFormatter.issues_to_table_data"
        ):
            with patch(
                "roadmap.common.formatters.export.issue_exporter.OutputFormatter"
            ) as mock_formatter:
                mock_formatter_instance = Mock()
                mock_formatter_instance.to_markdown.return_value = "| Test |"
                mock_formatter.return_value = mock_formatter_instance

                result = IssueExporter.export(issues, "markdown")  # type: ignore

                assert "Test" in result

    def test_export_invalid_format(self):
        """Test export with invalid format."""
        issues = [MockIssue()]

        with patch(
            "roadmap.common.formatters.export.issue_exporter.IssueTableFormatter.issues_to_table_data"
        ):
            with patch(
                "roadmap.common.formatters.export.issue_exporter.OutputFormatter"
            ):
                with pytest.raises(ValueError):
                    IssueExporter.export(issues, "invalid")  # type: ignore

    def test_export_with_custom_title(self):
        """Test export with custom title."""
        issues = [MockIssue()]

        with patch(
            "roadmap.common.formatters.export.issue_exporter.IssueTableFormatter.issues_to_table_data"
        ) as mock_table_data:
            with patch(
                "roadmap.common.formatters.export.issue_exporter.OutputFormatter"
            ) as mock_formatter:
                mock_formatter_instance = Mock()
                mock_formatter_instance.to_json.return_value = "{}"
                mock_formatter.return_value = mock_formatter_instance

                IssueExporter.export(issues, "json", title="Custom Title")  # type: ignore

                # Check that issues_to_table_data was called with title
                mock_table_data.assert_called_once()
                call_kwargs = mock_table_data.call_args[1]
                assert call_kwargs.get("title") == "Custom Title"

    def test_to_json_legacy(self):
        """Test legacy JSON export."""
        issues = [MockIssue("ISSUE-001", "Test")]

        def serializer(i):
            return {"id": i.id, "title": i.title}

        result = IssueExporter.to_json(issues, serializer)  # type: ignore

        # Result should be valid JSON
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["id"] == "ISSUE-001"

    def test_to_csv_legacy(self):
        """Test legacy CSV export."""
        issues = [MockIssue("ISSUE-001", "Test")]

        def serializer(i):
            return {
                "id": i.id,
                "title": i.title,
                "status": "open",
                "assignee": "John",
                "priority": "medium",
                "estimated_hours": "0",
                "milestone": "v1-0",
                "created": "2024-01-01",
                "updated": "2024-01-02",
            }

        result = IssueExporter.to_csv(issues, serializer)  # type: ignore

        # Check that CSV has header
        assert "id" in result
        assert "title" in result
        assert "ISSUE-001" in result

    def test_to_markdown_legacy(self):
        """Test legacy Markdown export."""
        issues = [MockIssue()]

        result = IssueExporter.to_markdown(issues)  # type: ignore

        # Should contain table format
        assert "|" in result
        assert "ISSUE-001" in result

    def test_csv_fields_are_defined(self):
        """Test that CSV fields are properly defined."""
        expected_fields = [
            "id",
            "title",
            "status",
            "assignee",
            "priority",
            "estimated_hours",
            "milestone",
            "created",
            "updated",
        ]
        assert IssueExporter.CSV_FIELDS == expected_fields

    def test_export_empty_list(self):
        """Test export with empty list."""
        with patch(
            "roadmap.common.formatters.export.issue_exporter.IssueTableFormatter.issues_to_table_data"
        ):
            with patch(
                "roadmap.common.formatters.export.issue_exporter.OutputFormatter"
            ) as mock_formatter:
                mock_formatter_instance = Mock()
                mock_formatter_instance.to_json.return_value = "[]"
                mock_formatter.return_value = mock_formatter_instance

                result = IssueExporter.export([], "json")

                assert result == "[]"

    def test_to_markdown_with_status_value(self):
        """Test Markdown export handles status enum values."""
        issue = MockIssue()
        result = IssueExporter.to_markdown([issue])  # type: ignore

        # Status should be included
        assert "ISSUE-001" in result
        assert "Test Issue" in result

    def test_to_markdown_without_estimated_hours_attr(self):
        """Test Markdown export when estimated_time_display is missing."""
        issue = Mock()
        issue.id = "ISSUE-001"
        issue.title = "Test"
        issue.status = Status.TODO
        issue.assignee = "John"
        issue.milestone = "v1-0"
        issue.estimated_time_display = None

        # Should handle missing attributes
        result = IssueExporter.to_markdown([issue])  # type: ignore

        assert "ISSUE-001" in result

    @pytest.mark.parametrize("format_type", ["json", "csv", "markdown"])
    def test_export_all_formats(self, format_type):
        """Test export with all valid formats."""
        issues = [MockIssue()]

        with patch(
            "roadmap.common.formatters.export.issue_exporter.IssueTableFormatter.issues_to_table_data"
        ):
            with patch(
                "roadmap.common.formatters.export.issue_exporter.OutputFormatter"
            ) as mock_formatter:
                mock_formatter_instance = Mock()
                mock_formatter_instance.to_json.return_value = "json"
                mock_formatter_instance.to_csv.return_value = "csv"
                mock_formatter_instance.to_markdown.return_value = "markdown"
                mock_formatter.return_value = mock_formatter_instance

                result = IssueExporter.export(issues, format_type)  # type: ignore

                assert result is not None

    def test_multiple_issues_export(self):
        """Test exporting multiple issues."""
        issues = [
            MockIssue("ISSUE-001", "First"),
            MockIssue("ISSUE-002", "Second"),
            MockIssue("ISSUE-003", "Third"),
        ]

        with patch(
            "roadmap.common.formatters.export.issue_exporter.IssueTableFormatter.issues_to_table_data"
        ):
            with patch(
                "roadmap.common.formatters.export.issue_exporter.OutputFormatter"
            ) as mock_formatter:
                mock_formatter_instance = Mock()
                mock_formatter_instance.to_json.return_value = "{}"
                mock_formatter.return_value = mock_formatter_instance

                result = IssueExporter.export(issues, "json")  # type: ignore

                assert result == "{}"

    def test_to_json_preserves_structure(self):
        """Test that to_json preserves issue structure."""
        issue = MockIssue("ISSUE-001", "Test Issue")

        def serializer(i):
            return {
                "id": i.id,
                "title": i.title,
                "status": "open",
            }

        result = IssueExporter.to_json([issue], serializer)  # type: ignore
        data = json.loads(result)

        assert data[0]["id"] == "ISSUE-001"
        assert data[0]["title"] == "Test Issue"

    def test_to_csv_handles_missing_fields(self):
        """Test that CSV export handles missing fields."""
        issue = Mock()
        issue.id = "ISSUE-001"

        def serializer(i):
            return {"id": i.id}  # Missing other fields

        result = IssueExporter.to_csv([issue], serializer)  # type: ignore

        # Should have header and at least one row
        lines = result.split("\n")
        assert len(lines) >= 2

    def test_export_calls_issues_to_table_data(self):
        """Test that export calls issues_to_table_data."""
        issues = [MockIssue()]

        with patch(
            "roadmap.common.formatters.export.issue_exporter.IssueTableFormatter.issues_to_table_data"
        ) as mock_table_data:
            with patch(
                "roadmap.common.formatters.export.issue_exporter.OutputFormatter"
            ):
                try:
                    IssueExporter.export(issues, "json")  # type: ignore
                except Exception:  # noqa: BLE001
                    pass

                mock_table_data.assert_called_once()
