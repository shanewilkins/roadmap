"""Tests for parser functionality."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from roadmap.domain import Issue, Milestone, MilestoneStatus, Priority, Status
from roadmap.parser import FrontmatterParser, IssueParser, MilestoneParser

pytestmark = pytest.mark.unit


class TestFrontmatterParser:
    """Test cases for FrontmatterParser."""

    def test_parse_content_with_frontmatter(self):
        """Test parsing content with YAML frontmatter."""
        content = """---
title: Test
value: 123
---

This is content.
"""

        frontmatter, body = FrontmatterParser.parse_content(content)

        assert frontmatter == {"title": "Test", "value": 123}
        assert body.strip() == "This is content."

    def test_parse_content_with_malformed_yaml(self):
        """Test parsing content with malformed YAML frontmatter."""
        content = """---
title: Test
invalid: [unclosed bracket
priority: high
---

This content has malformed YAML.
"""

        # Should raise ValueError for malformed YAML
        with pytest.raises(ValueError, match="Invalid YAML frontmatter"):
            FrontmatterParser.parse_content(content)

    def test_parse_content_without_frontmatter(self):
        """Test parsing content without frontmatter."""
        content = "Just regular markdown content without frontmatter."

        frontmatter, body = FrontmatterParser.parse_content(content)

        assert frontmatter == {}
        assert body == content

    def test_parse_content_with_empty_frontmatter(self):
        """Test parsing content with empty frontmatter."""
        content = """---
---

Content after empty frontmatter.
"""

        frontmatter, body = FrontmatterParser.parse_content(content)

        assert frontmatter == {}
        assert "Content after empty frontmatter." in body

    def test_parse_content_with_incomplete_frontmatter(self):
        """Test parsing content with incomplete frontmatter (no closing ---)."""
        content = """---
title: Test Issue
priority: high

Content without closing frontmatter delimiter.
"""

        frontmatter, body = FrontmatterParser.parse_content(content)

        # Should treat as no frontmatter when incomplete
        assert frontmatter == {}
        assert "title: Test Issue" in body

    def test_parse_content_invalid_yaml(self):
        """Test parsing content with invalid YAML."""
        content = """---
title: "Unclosed quote
value: 123
---

Content.
"""

        with pytest.raises(ValueError, match="Invalid YAML frontmatter"):
            FrontmatterParser.parse_content(content)


class TestIssueParser:
    """Test cases for IssueParser."""

    def test_parse_issue_file_basic(self):
        """Test parsing basic issue file."""
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
        assert issue.status == Status.TODO
        assert issue.id == "12345678"
        assert issue.content == "This is a test issue description."
        assert issue.created == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert issue.updated == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

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
        assert issue.priority == Priority.CRITICAL
        assert issue.status == Status.IN_PROGRESS
        assert issue.milestone == "v1.0"
        assert issue.labels == ["bug", "urgent"]
        assert issue.assignee == "user1"
        assert issue.github_issue == 123
        assert issue.id == "abcdef12"
        assert "More details here." in issue.content

    def test_save_issue_file(self):
        """Test saving issue to file."""
        issue = Issue(
            id="12345678",
            title="Test Issue",
            priority=Priority.HIGH,
            status=Status.TODO,
            content="This is a test issue.",
            created=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            updated=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
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
            milestone="v2.0",
            labels=["test"],
            content="Test description",
            created=datetime(2024, 1, 1, 12, 30, 45, tzinfo=timezone.utc),
            updated=datetime(2024, 1, 2, 15, 45, 30, tzinfo=timezone.utc),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            file_path = Path(f.name)

        # Save then parse
        IssueParser.save_issue_file(original_issue, file_path)
        parsed_issue = IssueParser.parse_issue_file(file_path)

        # Should be identical
        assert parsed_issue.id == original_issue.id
        assert parsed_issue.title == original_issue.title
        assert parsed_issue.priority == original_issue.priority
        assert parsed_issue.status == original_issue.status
        assert parsed_issue.milestone == original_issue.milestone
        assert parsed_issue.labels == original_issue.labels
        assert parsed_issue.content == original_issue.content
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

            with pytest.raises(ValueError, match="is not a valid Priority"):
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


class TestMilestoneParser:
    """Test cases for MilestoneParser."""

    def test_parse_milestone_file_basic(self):
        """Test parsing basic milestone file."""
        content = """---
name: v1.0
description: First release
status: open
created: "2024-01-01T00:00:00"
updated: "2024-01-01T00:00:00"
---

This is the first release milestone.

## Goals

- Feature A
- Feature B
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            milestone = MilestoneParser.parse_milestone_file(Path(f.name))

        assert milestone.name == "v1.0"
        assert milestone.description == "First release"
        assert milestone.status == MilestoneStatus.OPEN
        assert milestone.created == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert milestone.updated == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert "Goals" in milestone.content
        assert "Feature A" in milestone.content

    def test_parse_milestone_file_with_due_date(self):
        """Test parsing milestone file with due date."""
        content = """---
name: v2.0
description: Second release
status: closed
due_date: "2024-12-31T23:59:59"
github_milestone: 456
created: "2024-01-01T00:00:00"
updated: "2024-01-01T00:00:00"
---

Second release content.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            milestone = MilestoneParser.parse_milestone_file(Path(f.name))

        assert milestone.name == "v2.0"
        assert milestone.status == MilestoneStatus.CLOSED
        assert milestone.due_date == datetime(
            2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc
        )
        assert milestone.github_milestone == 456

    def test_save_milestone_file(self):
        """Test saving milestone to file."""
        milestone = Milestone(
            name="v1.0",
            description="First release",
            status=MilestoneStatus.OPEN,
            content="Milestone content",
            created=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            updated=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            file_path = Path(f.name)

        MilestoneParser.save_milestone_file(milestone, file_path)

        # Read back and verify
        saved_content = file_path.read_text()
        assert "name: v1.0" in saved_content
        assert "description: First release" in saved_content
        assert "status: open" in saved_content
        assert "Milestone content" in saved_content

    def test_roundtrip_serialization(self):
        """Test that saving and parsing are consistent."""
        original_milestone = Milestone(
            name="v1.5",
            description="Patch release",
            status=MilestoneStatus.OPEN,
            due_date=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
            content="Patch release content",
            created=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            updated=datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            file_path = Path(f.name)

        # Save then parse
        MilestoneParser.save_milestone_file(original_milestone, file_path)
        parsed_milestone = MilestoneParser.parse_milestone_file(file_path)

        # Should be identical
        assert parsed_milestone.name == original_milestone.name
        assert parsed_milestone.description == original_milestone.description
        assert parsed_milestone.status == original_milestone.status
        assert parsed_milestone.due_date == original_milestone.due_date
        assert parsed_milestone.content == original_milestone.content
        assert parsed_milestone.created == original_milestone.created
        assert parsed_milestone.updated == original_milestone.updated
