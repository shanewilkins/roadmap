"""Tests for enhanced YAML persistence functionality."""

import shutil
import tempfile
from pathlib import Path

import pytest

from roadmap.adapters.persistence.parser import IssueParser, MilestoneParser
from roadmap.adapters.persistence.persistence import (
    YAMLRecoveryManager,
)
from roadmap.core.domain import Issue, Milestone, MilestoneStatus, Priority, Status


class TestYAMLRecoveryManager:
    """Test the YAML recovery manager functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.backup_dir = self.temp_dir / "backups"
        self.recovery_manager = YAMLRecoveryManager(self.backup_dir)

        # Create test file
        self.test_file = self.temp_dir / "test.md"
        self.test_file.write_text("---\ntitle: Test\n---\n\nContent")

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_create_backup(self):
        """Test backup creation."""
        backup_path = self.recovery_manager.create_backup(self.test_file)

        assert backup_path.exists()
        assert backup_path.read_text() == self.test_file.read_text()
        assert "test_" in backup_path.name
        assert ".backup" in backup_path.name

    def test_list_backups(self):
        """Test listing backups."""
        import time

        # Create multiple backups with a small delay to ensure different timestamps
        backup1 = self.recovery_manager.create_backup(self.test_file)
        time.sleep(0.1)  # Small delay to ensure different timestamps
        backup2 = self.recovery_manager.create_backup(self.test_file)

        backups = self.recovery_manager.list_backups(self.test_file)
        assert len(backups) >= 1  # Should have at least one backup
        assert backup2 in backups or backup1 in backups  # At least one should be there

    @pytest.mark.parametrize(
        "yaml_content,is_valid,has_error",
        [
            ("title: Test\nstatus: todo", True, False),
            ("title: Valid YAML\ndescription: Another field", True, False),
            ("title: Test\nstatus: [unclosed list", False, True),
            ("invalid: [bad: yaml: syntax:", False, True),
        ],
    )
    def test_validate_yaml_syntax(self, yaml_content, is_valid, has_error):
        """Test YAML syntax validation with various inputs."""
        result_is_valid, error = self.recovery_manager.validate_yaml_syntax(
            yaml_content
        )
        assert result_is_valid == is_valid
        if has_error:
            assert error is not None
        else:
            assert error is None

    @pytest.mark.parametrize(
        "frontmatter,entity_type,expected_valid,error_pattern",
        [
            # Valid issue
            (
                {
                    "id": "a1b2c3d4",
                    "title": "Test Issue",
                    "priority": "high",
                    "status": "todo",
                },
                "issue",
                True,
                None,
            ),
            # Valid milestone
            ({"name": "Version 1.0", "status": "open"}, "milestone", True, None),
            # Issue with missing fields
            ({"id": "a1b2c3d4", "title": "Test Issue"}, "issue", False, "required"),
            # Issue with invalid enums
            (
                {
                    "id": "a1b2c3d4",
                    "title": "Test Issue",
                    "priority": "invalid_priority",
                    "status": "invalid_status",
                },
                "issue",
                False,
                "must be one of",
            ),
        ],
    )
    def test_validate_frontmatter_structure(
        self, frontmatter, entity_type, expected_valid, error_pattern
    ):
        """Test frontmatter structure validation for various scenarios."""
        is_valid, errors = self.recovery_manager.validate_frontmatter_structure(
            frontmatter, entity_type
        )
        assert is_valid == expected_valid
        if expected_valid:
            assert len(errors) == 0
        else:
            assert len(errors) > 0
            if error_pattern:
                error_str = " ".join(errors)
                assert error_pattern.lower() in error_str.lower()

    def test_fix_common_yaml_issues(self):
        """Test fixing common YAML formatting issues."""
        problematic_yaml = """title: Test: Issue with colons
description: This has @ and # characters
status: todo"""

        fixed_yaml = self.recovery_manager._fix_common_yaml_issues(problematic_yaml)

        # Should quote strings with special characters
        assert '"Test: Issue with colons"' in fixed_yaml
        assert '"This has @ and # characters"' in fixed_yaml
        assert "status: todo" in fixed_yaml  # Simple values shouldn't be quoted


class TestEnhancedParsers:
    """Test the enhanced parser methods."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_parse_issue_file_safe_valid_success_result(self):
        """Test safe parsing of valid issue file returns success."""
        issue_file = self.temp_dir / "test_issue.md"
        content = """---
id: a1b2c3d4
title: Test Issue
priority: high
status: todo
created: 2024-01-01T00:00:00
---

This is the issue content."""
        issue_file.write_text(content)

        success, issue, error = IssueParser.parse_issue_file_safe(issue_file)
        assert success
        assert issue is not None
        assert error is None

    def test_parse_issue_file_safe_valid_parsed_data(self):
        """Test safe parsing of valid issue file extracts data correctly."""
        issue_file = self.temp_dir / "test_issue.md"
        content = """---
id: a1b2c3d4
title: Test Issue
priority: high
status: todo
created: 2024-01-01T00:00:00
---

This is the issue content."""
        issue_file.write_text(content)

        success, issue, error = IssueParser.parse_issue_file_safe(issue_file)
        assert success
        assert issue is not None
        assert issue.id == "a1b2c3d4"
        assert issue.title == "Test Issue"
        assert issue.priority == Priority.HIGH
        assert issue.status == Status.TODO

    def test_parse_issue_file_safe_invalid(self):
        """Test safe parsing of invalid issue file."""
        issue_file = self.temp_dir / "test_issue.md"
        content = """---
id: a1b2c3d4
title: Test Issue
---

Missing required fields"""
        issue_file.write_text(content)

        success, issue, error = IssueParser.parse_issue_file_safe(issue_file)
        assert not success
        assert issue is None
        assert error is not None
        assert (
            "Missing required field" in error
            or "Field" in error
            or "is not a valid" in error
        )

    def test_save_issue_file_safe(self):
        """Test safe saving of issue file."""
        issue = Issue(
            id="a1b2c3d4",
            title="Test Issue",
            priority=Priority.HIGH,
            status=Status.TODO,
            content="Test content",
        )

        issue_file = self.temp_dir / "test_issue.md"

        success, message = IssueParser.save_issue_file_safe(issue, issue_file)
        assert success
        assert issue_file.exists()

        # Verify we can load it back
        success, loaded_issue, error = IssueParser.parse_issue_file_safe(issue_file)
        assert success
        assert loaded_issue is not None
        assert loaded_issue.id == issue.id
        assert loaded_issue.title == issue.title

    def test_parse_milestone_file_safe_valid(self):
        """Test safe parsing of valid milestone file."""
        milestone_file = self.temp_dir / "test_milestone.md"
        content = """---
name: Version 1.0
status: open
created: 2024-01-01T00:00:00
---

This is the milestone content."""
        milestone_file.write_text(content)

        success, milestone, error = MilestoneParser.parse_milestone_file_safe(
            milestone_file
        )
        assert success
        assert milestone is not None
        assert error is None
        assert milestone.name == "Version 1.0"
        assert milestone.status == MilestoneStatus.OPEN

    def test_save_milestone_file_safe(self):
        """Test safe saving of milestone file."""
        milestone = Milestone(
            name="Version 1.0",
            status=MilestoneStatus.OPEN,
            content="Milestone description",
        )

        milestone_file = self.temp_dir / "test_milestone.md"

        success, message = MilestoneParser.save_milestone_file_safe(
            milestone, milestone_file
        )
        assert success
        assert milestone_file.exists()

        # Verify we can load it back
        success, loaded_milestone, error = MilestoneParser.parse_milestone_file_safe(
            milestone_file
        )
        assert success
        assert loaded_milestone is not None
        assert loaded_milestone.name == milestone.name
        assert loaded_milestone.status == milestone.status
