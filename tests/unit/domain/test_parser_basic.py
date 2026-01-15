"""Tests for parser functionality."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from roadmap.adapters.persistence.parser import (
    FrontmatterParser,
    MilestoneParser,
)
from roadmap.core.domain import Milestone, MilestoneStatus

pytestmark = pytest.mark.unit


class TestFrontmatterParser:
    """Test cases for FrontmatterParser."""

    @pytest.mark.parametrize(
        "content,expected_frontmatter,expected_body_contains",
        [
            # Test with YAML frontmatter
            (
                """---
title: Test
value: 123
---

This is content.
""",
                {"title": "Test", "value": 123},
                "This is content.",
            ),
            # Test without frontmatter
            (
                "Just regular markdown content without frontmatter.",
                {},
                "Just regular markdown content without frontmatter.",
            ),
            # Test with empty frontmatter
            (
                """---
---

Content after empty frontmatter.
""",
                {},
                "Content after empty frontmatter.",
            ),
            # Test with incomplete frontmatter (no closing ---)
            (
                """---
title: Test Issue
priority: high

Content without closing frontmatter delimiter.
""",
                {},
                "title: Test Issue",
            ),
        ],
    )
    def test_parse_content_success(
        self, content, expected_frontmatter, expected_body_contains
    ):
        """Test successful parsing of content with various frontmatter formats."""
        frontmatter, body = FrontmatterParser.parse_content(content)
        assert frontmatter == expected_frontmatter
        assert expected_body_contains in body

    @pytest.mark.parametrize(
        "content,error_pattern",
        [
            # Malformed YAML with unclosed bracket
            (
                """---
title: Test
invalid: [unclosed bracket
priority: high
---

This content has malformed YAML.
""",
                "Invalid YAML frontmatter",
            ),
            # Invalid YAML with unclosed quote
            (
                """---
title: "Unclosed quote
value: 123
---

Content.
""",
                "Invalid YAML frontmatter",
            ),
        ],
    )
    def test_parse_content_errors(self, content, error_pattern):
        """Test parsing of content with invalid YAML."""
        with pytest.raises(ValueError, match=error_pattern):
            FrontmatterParser.parse_content(content)


class TestMilestoneParser:
    """Test cases for MilestoneParser."""

    @pytest.mark.parametrize(
        "name,headline,status,due_date_str,github_milestone,expected_has_due_date,expected_has_github_milestone,body_content",
        [
            (
                "v1.0",
                "First release",
                "open",
                None,
                None,
                False,
                False,
                "This is the first release milestone.\n\n## Goals\n\n- Feature A\n- Feature B",
            ),
            (
                "v2.0",
                "Second release",
                "closed",
                "2024-12-31T23:59:59",
                456,
                True,
                True,
                "Second release content.",
            ),
        ],
    )
    def test_parse_milestone_file(
        self,
        name,
        headline,
        status,
        due_date_str,
        github_milestone,
        expected_has_due_date,
        expected_has_github_milestone,
        body_content,
    ):
        """Test parsing milestone files with various configurations."""
        frontmatter_lines = [
            f"name: {name}",
            f"headline: {headline}",
            f"status: {status}",
        ]
        if due_date_str:
            frontmatter_lines.append(f'due_date: "{due_date_str}"')
        if github_milestone:
            frontmatter_lines.append(f"github_milestone: {github_milestone}")
        frontmatter_lines.extend(
            [
                'created: "2024-01-01T00:00:00"',
                'updated: "2024-01-01T00:00:00"',
            ]
        )

        content = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n" + body_content

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            milestone = MilestoneParser.parse_milestone_file(Path(f.name))

        assert milestone.name == name
        assert milestone.headline == headline
        assert milestone.content == body_content
        assert milestone.status == MilestoneStatus(status)
        assert milestone.created == datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert milestone.updated == datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

        if expected_has_due_date:
            assert milestone.due_date == datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC)
        if expected_has_github_milestone:
            assert milestone.github_milestone == 456

    def test_save_milestone_file(self):
        """Test saving milestone to file."""
        milestone = Milestone(
            name="v1.0",
            headline="First release",
            status=MilestoneStatus.OPEN,
            content="Milestone content",
            created=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            updated=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            file_path = Path(f.name)

        MilestoneParser.save_milestone_file(milestone, file_path)

        # Read back and verify
        saved_content = file_path.read_text()
        assert "name: v1.0" in saved_content
        assert "headline: First release" in saved_content
        assert "status: open" in saved_content
        assert "Milestone content" in saved_content

    def test_roundtrip_serialization_basic_fields(self):
        """Test that basic milestone fields survive roundtrip."""
        original_milestone = Milestone(
            name="v1.5",
            headline="Patch release",
            status=MilestoneStatus.OPEN,
            due_date=datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC),
            content="Patch release content",
            created=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
            updated=datetime(2024, 1, 2, 14, 30, 0, tzinfo=UTC),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            file_path = Path(f.name)

        # Save then parse
        MilestoneParser.save_milestone_file(original_milestone, file_path)
        parsed_milestone = MilestoneParser.parse_milestone_file(file_path)

        # Check basic fields
        assert parsed_milestone.name == original_milestone.name
        assert parsed_milestone.content == original_milestone.content
        assert parsed_milestone.status == original_milestone.status

    def test_roundtrip_serialization_dates_and_content(self):
        """Test that dates and content survive roundtrip."""
        original_milestone = Milestone(
            name="v1.5",
            headline="Patch release",
            status=MilestoneStatus.OPEN,
            due_date=datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC),
            content="Patch release content",
            created=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
            updated=datetime(2024, 1, 2, 14, 30, 0, tzinfo=UTC),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            file_path = Path(f.name)

        # Save then parse
        MilestoneParser.save_milestone_file(original_milestone, file_path)
        parsed_milestone = MilestoneParser.parse_milestone_file(file_path)

        # Check dates and content
        assert parsed_milestone.due_date == original_milestone.due_date
        assert parsed_milestone.content == original_milestone.content
        assert parsed_milestone.created == original_milestone.created
        assert parsed_milestone.updated == original_milestone.updated
