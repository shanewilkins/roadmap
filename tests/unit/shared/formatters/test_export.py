"""Unit tests for issue export functionality."""

import csv
import json
from io import StringIO
from unittest.mock import Mock

from roadmap.core.domain import Issue, IssueType, Priority, Status
from roadmap.shared.formatters.export import IssueExporter


class TestIssueExporter:
    """Test issue export formatting."""

    def create_sample_issue(self, **kwargs):
        """Create a sample issue for testing."""
        defaults = {
            "id": "ISS-123",
            "title": "Test Issue",
            "status": Status.TODO,
            "assignee": "testuser",
            "priority": Priority.MEDIUM,
            "estimated_hours": 8.0,
            "milestone": "v1.0",
            "issue_type": IssueType.FEATURE,
            "progress_display": "50%",
            "progress_percentage": 50,
            "estimated_time_display": "1d",
            "milestone_name": "v1.0",
            "is_backlog": False,
        }
        defaults.update(kwargs)
        return Mock(spec=Issue, **defaults)

    def test_to_json_single_issue(self):
        """to_json should format single issue as JSON."""
        issue = self.create_sample_issue()

        def serializer(i):
            return {"id": i.id, "title": i.title, "status": i.status.value}

        result = IssueExporter.to_json([issue], serializer)

        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["id"] == "ISS-123"
        assert parsed[0]["title"] == "Test Issue"
        assert parsed[0]["status"] == "todo"

    def test_to_json_multiple_issues(self):
        """to_json should format multiple issues as JSON array."""
        issues = [
            self.create_sample_issue(id="ISS-1", title="First"),
            self.create_sample_issue(id="ISS-2", title="Second"),
        ]

        def serializer(i):
            return {"id": i.id, "title": i.title}

        result = IssueExporter.to_json(issues, serializer)  # type: ignore[arg-type]

        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["id"] == "ISS-1"
        assert parsed[1]["id"] == "ISS-2"

    def test_to_json_empty_list(self):
        """to_json should handle empty issue list."""

        def serializer(i):
            return {"id": i.id}

        result = IssueExporter.to_json([], serializer)

        parsed = json.loads(result)
        assert parsed == []

    def test_to_json_includes_all_serializer_fields(self):
        """to_json should include all fields from serializer."""
        issue = self.create_sample_issue()

        def serializer(i):
            return {
                "id": i.id,
                "title": i.title,
                "status": i.status.value,
                "assignee": i.assignee,
                "priority": i.priority.value,
                "estimated_hours": i.estimated_hours,
                "milestone": i.milestone,
            }

        result = IssueExporter.to_json([issue], serializer)

        parsed = json.loads(result)
        assert parsed[0]["id"] == "ISS-123"
        assert parsed[0]["title"] == "Test Issue"
        assert parsed[0]["assignee"] == "testuser"
        assert parsed[0]["estimated_hours"] == 8.0

    def test_to_csv_single_issue(self):
        """to_csv should format single issue as CSV."""
        issue = self.create_sample_issue()

        def serializer(i):
            return {
                "id": i.id,
                "title": i.title,
                "status": i.status.value,
                "assignee": i.assignee,
                "priority": i.priority.value,
                "estimated_hours": i.estimated_hours,
                "milestone": i.milestone,
            }

        result = IssueExporter.to_csv([issue], serializer)

        # Parse the CSV
        reader = csv.DictReader(StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["id"] == "ISS-123"
        assert rows[0]["title"] == "Test Issue"
        assert rows[0]["assignee"] == "testuser"

    def test_to_csv_includes_header(self):
        """to_csv should include header row."""
        issue = self.create_sample_issue()

        def serializer(i):
            return {"id": i.id, "title": i.title}

        result = IssueExporter.to_csv([issue], serializer)

        lines = result.strip().split("\n")
        assert len(lines) >= 1  # At least header
        header = lines[0]

        # Check all expected fields in header
        assert "id" in header
        assert "title" in header
        assert "status" in header
        assert "assignee" in header

    def test_to_csv_handles_missing_fields(self):
        """to_csv should fill empty string for missing fields."""
        issue = self.create_sample_issue()

        def serializer(i):
            # Serializer only returns some fields
            return {"id": i.id, "title": i.title}

        result = IssueExporter.to_csv([issue], serializer)

        reader = csv.DictReader(StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["id"] == "ISS-123"
        assert rows[0]["title"] == "Test Issue"
        # Missing fields should be empty
        assert rows[0]["created"] == ""
        assert rows[0]["updated"] == ""

    def test_to_csv_multiple_issues(self):
        """to_csv should format multiple issues."""
        issues = [
            self.create_sample_issue(id="ISS-1", title="First"),
            self.create_sample_issue(id="ISS-2", title="Second"),
        ]

        def serializer(i):
            return {"id": i.id, "title": i.title}

        result = IssueExporter.to_csv(issues, serializer)  # type: ignore[arg-type]

        reader = csv.DictReader(StringIO(result))
        rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["id"] == "ISS-1"
        assert rows[1]["id"] == "ISS-2"

    def test_to_markdown_single_issue(self):
        """to_markdown should format single issue as table."""
        issue = self.create_sample_issue()

        result = IssueExporter.to_markdown([issue])

        lines = result.strip().split("\n")
        # Should have header, separator, and data row
        assert len(lines) == 3

        # Check header
        assert "id" in lines[0]
        assert "title" in lines[0]
        assert "status" in lines[0]

        # Check separator
        assert "|---|" in lines[1]

        # Check data row
        assert "ISS-123" in lines[2]
        assert "Test Issue" in lines[2]

    def test_to_markdown_multiple_issues(self):
        """to_markdown should format multiple issues as table."""
        issues = [
            self.create_sample_issue(id="ISS-1", title="First"),
            self.create_sample_issue(id="ISS-2", title="Second"),
        ]

        result = IssueExporter.to_markdown(issues)  # type: ignore[arg-type]

        lines = result.strip().split("\n")
        # Should have header, separator, and 2 data rows
        assert len(lines) == 4

        assert "ISS-1" in lines[2]
        assert "ISS-2" in lines[3]

    def test_to_markdown_with_none_values(self):
        """to_markdown should handle None values gracefully."""
        issue = self.create_sample_issue(assignee=None, milestone=None)

        result = IssueExporter.to_markdown([issue])

        # Should not raise exception and should contain the row
        assert "ISS-123" in result

    def test_to_markdown_uses_estimated_time_display_if_available(self):
        """to_markdown should prefer estimated_time_display over estimated_hours."""
        issue = self.create_sample_issue(estimated_hours=8.0)
        issue.estimated_time_display = "1d"

        result = IssueExporter.to_markdown([issue])

        assert "1d" in result

    def test_to_markdown_handles_status_enum(self):
        """to_markdown should handle Status enum values."""
        issue = self.create_sample_issue(status=Status.IN_PROGRESS)

        result = IssueExporter.to_markdown([issue])

        assert "in-progress" in result

    def test_to_markdown_empty_list(self):
        """to_markdown should handle empty issue list."""
        result = IssueExporter.to_markdown([])

        lines = result.strip().split("\n")
        # Should still have header and separator
        assert len(lines) == 2
