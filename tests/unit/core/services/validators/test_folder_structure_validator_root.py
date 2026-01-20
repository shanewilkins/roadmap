"""Tests for folder structure validator."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.core.services.validator_base import HealthStatus
from roadmap.core.services.validators.folder_structure_validator import (
    FolderStructureValidator,
)


class TestFolderStructureValidatorBasics:
    """Tests for basic FolderStructureValidator functionality."""

    def test_get_check_name(self):
        """Test that check name is correct."""
        assert FolderStructureValidator.get_check_name() == "folder_structure"

    def test_perform_check_nonexistent_directory(self):
        """Test perform_check when issues directory doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            status, message = FolderStructureValidator.perform_check()

            assert status == HealthStatus.HEALTHY
            assert "not initialized" in message.lower()

    def test_perform_check_with_existing_directory(self):
        """Test perform_check with existing issues directory."""
        with patch("pathlib.Path.exists", return_value=True):
            status, message = FolderStructureValidator.perform_check()

            assert status == HealthStatus.HEALTHY
            assert "simplified" in message.lower()


class TestCheckRootIssues:
    """Tests for _check_root_issues method."""

    def test_check_root_issues_no_issues(self, temp_dir_context):
        """Test checking root issues when none exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            core = Mock()
            misplaced = []

            FolderStructureValidator._check_root_issues(issues_dir, core, misplaced)

            assert misplaced == []

    def test_check_root_issues_misplaced_issue(self, temp_dir_context):
        """Test detecting misplaced issue in root with milestone assigned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create issue file in root (8 hex char issue ID format)
            issue_file = issues_dir / "a1b2c3d4-Test Issue.md"
            issue_file.write_text("# Test Issue")

            # Create milestone folder
            milestone_dir = issues_dir / "v1.0"
            milestone_dir.mkdir()

            # Mock core and issue service
            mock_issue = Mock()
            mock_issue.id = "a1b2c3d4"
            mock_issue.title = "Test Issue"
            mock_issue.milestone = "v1.0"

            core = Mock()
            core.issue_service.get_issue.return_value = mock_issue

            misplaced = []
            FolderStructureValidator._check_root_issues(issues_dir, core, misplaced)

            assert len(misplaced) == 1
            assert misplaced[0]["issue_id"] == "a1b2c3d4"
            assert misplaced[0]["assigned_milestone"] == "v1.0"
            assert "a1b2c3d4" in misplaced[0]["current_location"]

    def test_check_root_issues_with_backup_file(self, temp_dir_context):
        """Test that backup files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create backup file
            backup_file = issues_dir / "a1b2c3d4-Issue.md.backup"
            backup_file.write_text("# Backup")

            core = Mock()
            misplaced = []

            FolderStructureValidator._check_root_issues(issues_dir, core, misplaced)

            assert misplaced == []
            core.issue_service.get_issue.assert_not_called()

    def test_check_root_issues_no_milestone_assigned(self, temp_dir_context):
        """Test that issues without milestone are not flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create issue file
            issue_file = issues_dir / "a1b2c3d4-Issue.md"
            issue_file.write_text("# Issue")

            # Mock issue without milestone
            mock_issue = Mock()
            mock_issue.id = "a1b2c3d4"
            mock_issue.milestone = None

            core = Mock()
            core.issue_service.get_issue.return_value = mock_issue

            misplaced = []
            FolderStructureValidator._check_root_issues(issues_dir, core, misplaced)

            assert misplaced == []

    def test_check_root_issues_milestone_folder_nonexistent(self, temp_dir_context):
        """Test that missing milestone folder doesn't cause issue reporting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create issue file
            issue_file = issues_dir / "a1b2c3d4-Issue.md"
            issue_file.write_text("# Issue")

            # Mock issue with milestone that doesn't exist
            mock_issue = Mock()
            mock_issue.id = "a1b2c3d4"
            mock_issue.milestone = "v1.0"

            core = Mock()
            core.issue_service.get_issue.return_value = mock_issue

            misplaced = []
            FolderStructureValidator._check_root_issues(issues_dir, core, misplaced)

            # Should not be flagged if milestone folder doesn't exist
            assert misplaced == []

    def test_check_root_issues_exception_handling(self, temp_dir_context):
        """Test that exceptions during processing are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create issue file
            issue_file = issues_dir / "a1b2c3d4-Issue.md"
            issue_file.write_text("# Issue")

            # Mock service that raises exception
            core = Mock()
            core.issue_service.get_issue.side_effect = Exception("DB error")

            misplaced = []
            # Should not raise, just continue
            FolderStructureValidator._check_root_issues(issues_dir, core, misplaced)

            assert misplaced == []

    @pytest.mark.parametrize(
        "filename,should_extract",
        [
            ("a1b2c3d4-Issue.md", True),
            ("f0e1d2c3-Another.md", True),
            ("invalid.md", False),
            ("no-number.md", False),
        ],
    )
    def test_check_root_issues_filename_parsing(
        self, filename, should_extract, temp_dir_context
    ):
        """Test various filename formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            issue_file = issues_dir / filename
            issue_file.write_text("# Issue")

            core = Mock()
            core.issue_service.get_issue.return_value = None

            misplaced = []
            FolderStructureValidator._check_root_issues(issues_dir, core, misplaced)

            if should_extract:
                core.issue_service.get_issue.assert_called()
            else:
                core.issue_service.get_issue.assert_not_called()
