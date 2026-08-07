"""Tests for parser functionality."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from roadmap.adapters.persistence.parser import (
    IssueParser,
)
from roadmap.core.domain import Issue, Priority, Status

pytestmark = pytest.mark.unit


class TestIssueParser:
    """Test cases for IssueParser."""

    def test_parse_issue_file_basic_title_and_priority(self):
        """Test parsing basic issue file returns title and priority."""
        content = """---
id: "12345678"
title: Test Issue
priority: high
status: todo
created: "2024-01-01T00:00:00"
updated: "2024-01-01T00:00:00"
---

This is a test issue description.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            issue = IssueParser.parse_issue_file(Path(f.name))

        assert issue.title == "Test Issue"
        assert issue.priority == Priority.HIGH

    def test_parse_issue_file_basic_status_and_id(self):
        """Test parsing basic issue file returns status and id."""
        content = """---
id: "12345678"
title: Test Issue
priority: high
status: todo
created: "2024-01-01T00:00:00"
updated: "2024-01-01T00:00:00"
---

This is a test issue description.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            issue = IssueParser.parse_issue_file(Path(f.name))

        assert issue.status == Status.TODO
        assert issue.id == "12345678"

    def test_parse_issue_file_basic_content_and_dates(self):
        """Test parsing basic issue file returns content and dates."""
        content = """---
id: "12345678"
title: Test Issue
priority: high
status: todo
created: "2024-01-01T00:00:00"
updated: "2024-01-01T00:00:00"
---

This is a test issue description.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            issue = IssueParser.parse_issue_file(Path(f.name))

        assert issue.content == "This is a test issue description."
        assert issue.created == datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert issue.updated == datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

    def test_parse_issue_file_with_all_fields(self):
        """Test parsing issue file with all fields."""
        content = """---
id: "abcdef12"
title: Complex Issue
priority: critical
status: in-progress
milestone: v1.0
labels:
  - bug
  - urgent
assignee: user1
github_issue: 123
created: "2024-01-01T00:00:00"
updated: "2024-01-02T00:00:00"
---

This is a complex issue with all fields.

## Details

More details here.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            issue = IssueParser.parse_issue_file(Path(f.name))

        assert issue.title == "Complex Issue"
        assert issue.id == "abcdef12"

    def test_parse_issue_file_priority_and_status(self):
        """Test parsing issue priority and status fields."""
        content = """---
id: "abcdef12"
title: Complex Issue
priority: critical
status: in-progress
---

Test content.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            issue = IssueParser.parse_issue_file(Path(f.name))

        assert issue.priority == Priority.CRITICAL
        assert issue.status == Status.IN_PROGRESS

    def test_parse_issue_file_milestone_and_assignee(self):
        """Test parsing issue milestone and assignee."""
        content = """---
id: "abcdef12"
title: Complex Issue
milestone: v1-0
assignee: user1
---

Test content.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            issue = IssueParser.parse_issue_file(Path(f.name))

        assert issue.milestone == "v1-0"
        assert issue.assignee == "user1"

    def test_parse_issue_file_labels_and_github(self):
        """Test parsing issue labels and GitHub issue number."""
        content = """---
id: "abcdef12"
title: Complex Issue
labels:
  - bug
  - urgent
github_issue: 123
---

Test content.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            issue = IssueParser.parse_issue_file(Path(f.name))

        assert issue.labels == ["bug", "urgent"]
        assert issue.github_issue == 123

    def test_parse_issue_file_content(self):
        """Test parsing issue content section."""
        content = """---
id: "abcdef12"
title: Complex Issue
---

This is a complex issue with all fields.

## Details

More details here.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            issue = IssueParser.parse_issue_file(Path(f.name))

        assert "More details here." in issue.content

    def test_save_issue_file(self):
        """Test saving issue to file."""
        issue = Issue(
            id="12345678",
            title="Test Issue",
            priority=Priority.HIGH,
            status=Status.TODO,
            content="This is a test issue.",
            created=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            updated=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            file_path = Path(f.name)

        IssueParser.save_issue_file(issue, file_path)

        # Read back and verify
        saved_content = file_path.read_text()
        assert "title: Test Issue" in saved_content
        assert "priority: high" in saved_content
        assert "status: todo" in saved_content
        assert "This is a test issue." in saved_content

    def test_roundtrip_serialization(self):
        """Test that saving and parsing are consistent."""
        original_issue = Issue(
            id="12345678",
            title="Roundtrip Test",
            priority=Priority.MEDIUM,
            status=Status.REVIEW,
            milestone="v2-0",
            labels=["test"],
            content="Test description",
            created=datetime(2024, 1, 1, 12, 30, 45, tzinfo=UTC),
            updated=datetime(2024, 1, 2, 15, 45, 30, tzinfo=UTC),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            file_path = Path(f.name)

        # Save then parse
        IssueParser.save_issue_file(original_issue, file_path)
        parsed_issue = IssueParser.parse_issue_file(file_path)

        # Check core fields
        assert parsed_issue.id == original_issue.id
        assert parsed_issue.title == original_issue.title
        assert parsed_issue.content == original_issue.content

    def test_roundtrip_metadata_fields(self):
        """Test that metadata is preserved in roundtrip."""
        original_issue = Issue(
            id="12345678",
            title="Roundtrip Test",
            priority=Priority.MEDIUM,
            status=Status.REVIEW,
            milestone="v2-0",
            labels=["test"],
            content="Test description",
            created=datetime(2024, 1, 1, 12, 30, 45, tzinfo=UTC),
            updated=datetime(2024, 1, 2, 15, 45, 30, tzinfo=UTC),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            file_path = Path(f.name)

        # Save then parse
        IssueParser.save_issue_file(original_issue, file_path)
        parsed_issue = IssueParser.parse_issue_file(file_path)

        # Check metadata fields
        assert parsed_issue.priority == original_issue.priority
        assert parsed_issue.status == original_issue.status
        assert parsed_issue.milestone == original_issue.milestone
        assert parsed_issue.labels == original_issue.labels

    def test_roundtrip_timestamps(self):
        """Test that timestamps are preserved in roundtrip."""
        original_issue = Issue(
            id="12345678",
            title="Roundtrip Test",
            created=datetime(2024, 1, 1, 12, 30, 45, tzinfo=UTC),
            updated=datetime(2024, 1, 2, 15, 45, 30, tzinfo=UTC),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            file_path = Path(f.name)

        # Save then parse
        IssueParser.save_issue_file(original_issue, file_path)
        parsed_issue = IssueParser.parse_issue_file(file_path)

        # Check timestamp fields
        assert parsed_issue.created == original_issue.created
        assert parsed_issue.updated == original_issue.updated

    def test_parse_issue_file_with_missing_required_fields(self):
        """Test parsing issue file with missing required fields."""
        content = """---
priority: high
status: todo
created: "2024-01-01T00:00:00"
updated: "2024-01-01T00:00:00"
---

Issue without id or title.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            # Should raise ValidationError (from pydantic) when required fields are missing
            with pytest.raises(Exception, match="Field required"):
                IssueParser.parse_issue_file(Path(f.name))

    def test_parse_issue_file_with_invalid_enum_values(self):
        """Test parsing issue file with invalid enum values."""
        content = """---
id: "12345678"
title: Test Issue
priority: invalid_priority
status: invalid_status
created: "2024-01-01T00:00:00"
updated: "2024-01-01T00:00:00"
---

Issue with invalid enum values.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            with pytest.raises(ValueError, match="Invalid priority"):
                IssueParser.parse_issue_file(Path(f.name))

    def test_parse_issue_file_with_invalid_dates(self):
        """Test parsing issue file with invalid date formats."""
        content = """---
id: "12345678"
title: Test Issue
priority: high
status: todo
created: "invalid-date-format"
updated: "2024-01-01T00:00:00"
---

Issue with invalid date format.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            with pytest.raises(ValueError, match="Input should be a valid datetime"):
                IssueParser.parse_issue_file(Path(f.name))

    def test_parse_issue_file_nonexistent(self):
        """Test parsing non-existent issue file."""
        with pytest.raises(FileNotFoundError):
            IssueParser.parse_issue_file(Path("/nonexistent/file.md"))

    def test_parse_issue_file_empty(self):
        """Test parsing empty issue file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("")
            f.flush()

            with pytest.raises(Exception, match="Field required"):
                IssueParser.parse_issue_file(Path(f.name))

    def test_parse_issue_file_with_corrupted_frontmatter(self):
        """Test parsing issue file with corrupted frontmatter."""
        content = """---
id: "12345678"
title: Test Issue
priority: [invalid yaml structure
status: todo
---

Issue with corrupted YAML.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            # Should raise an error due to invalid YAML
            with pytest.raises(ValueError):
                IssueParser.parse_issue_file(Path(f.name))
