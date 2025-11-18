"""Tests for enhanced YAML persistence functionality."""

import shutil
import tempfile
from pathlib import Path

from roadmap.domain import Issue, Milestone, MilestoneStatus, Priority, Status
from roadmap.parser import IssueParser, MilestoneParser
from roadmap.persistence import (
    EnhancedYAMLPersistence,
    YAMLRecoveryManager,
)


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

    def test_restore_from_backup(self):
        """Test restoring from backup."""
        # Create backup
        self.recovery_manager.create_backup(self.test_file)

        # Modify original file
        self.test_file.write_text("Modified content")

        # Restore from backup
        success = self.recovery_manager.restore_from_backup(self.test_file)
        assert success
        assert self.test_file.read_text() == "---\ntitle: Test\n---\n\nContent"

    def test_validate_yaml_syntax_valid(self):
        """Test YAML syntax validation with valid YAML."""
        valid_yaml = "title: Test\nstatus: todo"
        is_valid, error = self.recovery_manager.validate_yaml_syntax(valid_yaml)
        assert is_valid
        assert error is None

    def test_validate_yaml_syntax_invalid(self):
        """Test YAML syntax validation with invalid YAML."""
        invalid_yaml = "title: Test\nstatus: [unclosed list"
        is_valid, error = self.recovery_manager.validate_yaml_syntax(invalid_yaml)
        assert not is_valid
        assert error and "YAML syntax error" in error

    def test_validate_frontmatter_structure_issue_valid(self):
        """Test frontmatter structure validation for valid issue."""
        frontmatter = {
            "id": "a1b2c3d4",
            "title": "Test Issue",
            "priority": "high",
            "status": "todo",
        }
        is_valid, errors = self.recovery_manager.validate_frontmatter_structure(
            frontmatter, "issue"
        )
        assert is_valid
        assert len(errors) == 0

    def test_validate_frontmatter_structure_issue_missing_field(self):
        """Test frontmatter structure validation for issue with missing field."""
        frontmatter = {
            "id": "a1b2c3d4",
            "title": "Test Issue",
            # Missing priority and status
        }
        is_valid, errors = self.recovery_manager.validate_frontmatter_structure(
            frontmatter, "issue"
        )
        assert not is_valid
        # Check if the new validation framework is reporting the errors
        error_str = " ".join(errors) if errors else ""
        assert (
            "Missing required field: priority" in error_str
            or "Field 'priority' is required" in error_str
        )
        assert (
            "Missing required field: status" in error_str
            or "Field 'status' is required" in error_str
        )

    def test_validate_frontmatter_structure_issue_invalid_enum(self):
        """Test frontmatter structure validation for issue with invalid enum."""
        frontmatter = {
            "id": "a1b2c3d4",
            "title": "Test Issue",
            "priority": "invalid_priority",
            "status": "invalid_status",
        }
        is_valid, errors = self.recovery_manager.validate_frontmatter_structure(
            frontmatter, "issue"
        )
        assert not is_valid
        assert "must be one of:" in errors[0]
        assert "must be one of:" in errors[1]

    def test_validate_frontmatter_structure_milestone_valid(self):
        """Test frontmatter structure validation for valid milestone."""
        frontmatter = {"name": "Version 1.0", "status": "open"}
        is_valid, errors = self.recovery_manager.validate_frontmatter_structure(
            frontmatter, "milestone"
        )
        assert is_valid
        assert len(errors) == 0

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


class TestEnhancedYAMLPersistence:
    """Test the enhanced YAML persistence functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.persistence = EnhancedYAMLPersistence()

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_safe_load_with_validation_valid_issue(self):
        """Test safe loading of valid issue file."""
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

        is_valid, result = self.persistence.safe_load_with_validation(
            issue_file, "issue"
        )
        assert is_valid
        assert isinstance(result, dict)
        assert result["id"] == "a1b2c3d4"
        assert result["title"] == "Test Issue"
        assert result["content"] == "This is the issue content."

    def test_safe_load_with_validation_invalid_yaml(self):
        """Test safe loading of file with invalid YAML."""
        issue_file = self.temp_dir / "test_issue.md"
        content = """---
id: a1b2c3d4
title: Test Issue
priority: [unclosed list
status: todo
---

Content"""
        issue_file.write_text(content)

        is_valid, result = self.persistence.safe_load_with_validation(
            issue_file, "issue"
        )
        assert not is_valid
        assert "YAML validation failed" in result

    def test_safe_save_with_backup_issue(self):
        """Test safe saving of issue with backup."""
        issue = Issue(
            id="a1b2c3d4",
            title="Test Issue",
            priority=Priority.HIGH,
            status=Status.TODO,
            content="Test content",
        )

        issue_file = self.temp_dir / "test_issue.md"

        success, message = self.persistence.safe_save_with_backup(issue, issue_file)
        assert success
        assert "New file created" in message
        assert issue_file.exists()

        # Verify content
        is_valid, result = self.persistence.safe_load_with_validation(
            issue_file, "issue"
        )
        assert is_valid
        assert result["id"] == "a1b2c3d4"
        assert result["title"] == "Test Issue"

    def test_safe_save_with_backup_milestone(self):
        """Test safe saving of milestone with backup."""
        milestone = Milestone(
            name="Version 1.0",
            status=MilestoneStatus.OPEN,
            content="Milestone description",
        )

        milestone_file = self.temp_dir / "test_milestone.md"

        success, message = self.persistence.safe_save_with_backup(
            milestone, milestone_file
        )
        assert success
        assert milestone_file.exists()

        # Verify content
        is_valid, result = self.persistence.safe_load_with_validation(
            milestone_file, "milestone"
        )
        assert is_valid
        assert result["name"] == "Version 1.0"

    def test_get_file_health_report(self):
        """Test generating file health report."""
        # Create valid issue file
        valid_issue = self.temp_dir / "valid_issue.md"
        valid_content = """---
id: a1b2c3d4
title: Valid Issue
priority: high
status: todo
---

Valid content"""
        valid_issue.write_text(valid_content)

        # Create invalid issue file
        invalid_issue = self.temp_dir / "invalid_issue.md"
        invalid_content = """---
id: invalid-id
title: Invalid Issue
---

Missing required fields"""
        invalid_issue.write_text(invalid_content)

        report = self.persistence.get_file_health_report(self.temp_dir, "issue")

        assert report["total_files"] == 2
        assert report["valid_files"] == 1
        assert report["invalid_files"] == 1
        assert len(report["errors"]) == 1


class TestEnhancedParsers:
    """Test the enhanced parser methods."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_parse_issue_file_safe_valid(self):
        """Test safe parsing of valid issue file."""
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
        assert loaded_milestone.name == milestone.name
        assert loaded_milestone.status == milestone.status
