"""Tests for folder structure validator."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pytest

from roadmap.core.services.base_validator import HealthStatus
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

    def test_check_root_issues_no_issues(self):
        """Test checking root issues when none exist."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            core = Mock()
            misplaced = []

            FolderStructureValidator._check_root_issues(issues_dir, core, misplaced)

            assert misplaced == []

    def test_check_root_issues_misplaced_issue(self):
        """Test detecting misplaced issue in root with milestone assigned."""
        with TemporaryDirectory() as tmpdir:
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

    def test_check_root_issues_with_backup_file(self):
        """Test that backup files are skipped."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create backup file
            backup_file = issues_dir / "a1b2c3d4-Issue.md.backup"
            backup_file.write_text("# Backup")

            core = Mock()
            misplaced = []

            FolderStructureValidator._check_root_issues(issues_dir, core, misplaced)

            assert misplaced == []
            core.issue_service.get_issue.assert_not_called()

    def test_check_root_issues_no_milestone_assigned(self):
        """Test that issues without milestone are not flagged."""
        with TemporaryDirectory() as tmpdir:
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

    def test_check_root_issues_milestone_folder_nonexistent(self):
        """Test that missing milestone folder doesn't cause issue reporting."""
        with TemporaryDirectory() as tmpdir:
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

    def test_check_root_issues_exception_handling(self):
        """Test that exceptions during processing are handled gracefully."""
        with TemporaryDirectory() as tmpdir:
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
    def test_check_root_issues_filename_parsing(self, filename, should_extract):
        """Test various filename formats."""
        with TemporaryDirectory() as tmpdir:
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


class TestProcessMilestoneFile:
    """Tests for _process_milestone_file method."""

    def test_process_milestone_file_orphaned_issue(self):
        """Test detecting orphaned issue in milestone folder."""
        with TemporaryDirectory() as tmpdir:
            milestone_dir = Path(tmpdir) / "v1.0"
            milestone_dir.mkdir()

            issue_file = milestone_dir / "a1b2c3d4-Issue.md"
            issue_file.write_text("# Issue")

            # Mock issue without milestone assignment
            mock_issue = Mock()
            mock_issue.id = "a1b2c3d4"
            mock_issue.title = "Orphaned Issue"
            mock_issue.milestone = None

            core = Mock()
            core.issue_service.get_issue.return_value = mock_issue

            orphaned = []
            FolderStructureValidator._process_milestone_file(
                issue_file, core, milestone_dir, orphaned
            )

            assert len(orphaned) == 1
            assert orphaned[0]["issue_id"] == "a1b2c3d4"
            assert orphaned[0]["folder"] == "v1.0"

    def test_process_milestone_file_backup_skipped(self):
        """Test that backup files in milestone folders are skipped."""
        with TemporaryDirectory() as tmpdir:
            milestone_dir = Path(tmpdir) / "v1.0"
            milestone_dir.mkdir()
            issue_file = milestone_dir / "a1b2c3d4-Issue.md.backup"
            issue_file.write_text("# Backup")

            core = Mock()
            orphaned = []

            FolderStructureValidator._process_milestone_file(
                issue_file, core, milestone_dir, orphaned
            )

            assert orphaned == []
            core.issue_service.get_issue.assert_not_called()

    def test_process_milestone_file_with_milestone_assignment(self):
        """Test that correctly placed issues are not flagged."""
        with TemporaryDirectory() as tmpdir:
            milestone_dir = Path(tmpdir) / "v1.0"
            milestone_dir.mkdir()

            issue_file = milestone_dir / "a1b2c3d4-Issue.md"
            issue_file.write_text("# Issue")

            # Mock issue with correct milestone assignment
            mock_issue = Mock()
            mock_issue.id = "a1b2c3d4"
            mock_issue.milestone = "v1.0"

            core = Mock()
            core.issue_service.get_issue.return_value = mock_issue

            orphaned = []
            FolderStructureValidator._process_milestone_file(
                issue_file, core, milestone_dir, orphaned
            )

            assert orphaned == []

    def test_process_milestone_file_exception_handling(self):
        """Test exception handling during file processing."""
        with TemporaryDirectory() as tmpdir:
            milestone_dir = Path(tmpdir) / "v1.0"
            milestone_dir.mkdir()
            issue_file = milestone_dir / "a1b2c3d4-Issue.md"
            issue_file.write_text("# Issue")

            core = Mock()
            core.issue_service.get_issue.side_effect = Exception("Error")

            orphaned = []
            # Should not raise
            FolderStructureValidator._process_milestone_file(
                issue_file, core, milestone_dir, orphaned
            )

            assert orphaned == []


class TestCheckMilestoneFolders:
    """Tests for _check_milestone_folders method."""

    def test_check_milestone_folders_no_folders(self):
        """Test when no milestone folders exist."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            core = Mock()
            orphaned = []

            FolderStructureValidator._check_milestone_folders(
                issues_dir, core, orphaned
            )

            assert orphaned == []

    def test_check_milestone_folders_skips_hidden(self):
        """Test that hidden folders are skipped."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create hidden folder
            hidden_dir = issues_dir / ".hidden"
            hidden_dir.mkdir()
            (hidden_dir / "a1b2c3d4-Issue.md").write_text("# Issue")

            core = Mock()
            orphaned = []

            FolderStructureValidator._check_milestone_folders(
                issues_dir, core, orphaned
            )

            assert orphaned == []
            core.issue_service.get_issue.assert_not_called()

    def test_check_milestone_folders_skips_backlog(self):
        """Test that backlog folder is skipped."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create backlog folder
            backlog_dir = issues_dir / "backlog"
            backlog_dir.mkdir()
            (backlog_dir / "a1b2c3d4-Issue.md").write_text("# Issue")

            core = Mock()
            orphaned = []

            FolderStructureValidator._check_milestone_folders(
                issues_dir, core, orphaned
            )

            assert orphaned == []
            core.issue_service.get_issue.assert_not_called()

    def test_check_milestone_folders_processes_milestone_files(self):
        """Test that milestone folders are processed."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create milestone folder with orphaned issue
            v1_dir = issues_dir / "v1.0"
            v1_dir.mkdir()
            (v1_dir / "a1b2c3d4-Issue.md").write_text("# Issue")

            mock_issue = Mock()
            mock_issue.id = "a1b2c3d4"
            mock_issue.title = "Issue"
            mock_issue.milestone = None

            core = Mock()
            core.issue_service.get_issue.return_value = mock_issue

            orphaned = []
            FolderStructureValidator._check_milestone_folders(
                issues_dir, core, orphaned
            )

            assert len(orphaned) == 1
            assert orphaned[0]["folder"] == "v1.0"

    def test_check_milestone_folders_multiple_milestones(self):
        """Test processing multiple milestone folders."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create multiple milestone folders
            for version in ["v1.0", "v2.0", "v3.0"]:
                version_dir = issues_dir / version
                version_dir.mkdir()
                (version_dir / "a1b2c3d4-Issue.md").write_text("# Issue")

            mock_issue = Mock()
            mock_issue.id = "a1b2c3d4"
            mock_issue.milestone = None

            core = Mock()
            core.issue_service.get_issue.return_value = mock_issue

            orphaned = []
            FolderStructureValidator._check_milestone_folders(
                issues_dir, core, orphaned
            )

            # Should find 3 orphaned issues
            assert len(orphaned) == 3


class TestScanForFolderStructureIssues:
    """Tests for scan_for_folder_structure_issues method."""

    def test_scan_no_issues(self):
        """Test scan when no issues are found."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            core = Mock()

            result = FolderStructureValidator.scan_for_folder_structure_issues(
                issues_dir, core
            )

            assert result == {}

    def test_scan_finds_misplaced_issues(self):
        """Test scan detecting misplaced issues."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create issue in root with milestone
            (issues_dir / "a1b2c3d4-Issue.md").write_text("# Issue")
            (issues_dir / "v1.0").mkdir()

            mock_issue = Mock()
            mock_issue.id = "a1b2c3d4"
            mock_issue.title = "Misplaced"
            mock_issue.milestone = "v1.0"

            core = Mock()
            core.issue_service.get_issue.return_value = mock_issue

            result = FolderStructureValidator.scan_for_folder_structure_issues(
                issues_dir, core
            )

            assert "misplaced" in result
            assert len(result["misplaced"]) == 1

    def test_scan_finds_orphaned_issues(self):
        """Test scan detecting orphaned issues."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create orphaned issue in milestone folder
            v1_dir = issues_dir / "v1.0"
            v1_dir.mkdir()
            (v1_dir / "a1b2c3d4-Issue.md").write_text("# Issue")

            mock_issue = Mock()
            mock_issue.id = "a1b2c3d4"
            mock_issue.title = "Orphaned"
            mock_issue.milestone = None

            core = Mock()
            core.issue_service.get_issue.return_value = mock_issue

            result = FolderStructureValidator.scan_for_folder_structure_issues(
                issues_dir, core
            )

            assert "orphaned" in result
            assert len(result["orphaned"]) == 1

    def test_scan_finds_both_types(self):
        """Test scan finding both misplaced and orphaned issues."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create misplaced issue in root
            (issues_dir / "a1b2c3d4-Issue1.md").write_text("# Issue 1")

            # Create orphaned issue in milestone
            v1_dir = issues_dir / "v1.0"
            v1_dir.mkdir()
            (v1_dir / "f0e1d2c3-Issue2.md").write_text("# Issue 2")

            def mock_get_issue(issue_id):
                if issue_id == "a1b2c3d4":
                    issue = Mock()
                    issue.id = "a1b2c3d4"
                    issue.title = "Misplaced"
                    issue.milestone = "v1.0"
                    return issue
                elif issue_id == "f0e1d2c3":
                    issue = Mock()
                    issue.id = "f0e1d2c3"
                    issue.title = "Orphaned"
                    issue.milestone = None
                    return issue
                return None

            core = Mock()
            core.issue_service.get_issue.side_effect = mock_get_issue

            result = FolderStructureValidator.scan_for_folder_structure_issues(
                issues_dir, core
            )

            assert len(result["misplaced"]) == 1
            assert len(result["orphaned"]) == 1

    def test_scan_exception_handling(self):
        """Test that exceptions during scan are handled gracefully."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            (issues_dir / "a1b2c3d4-Issue.md").write_text("# Issue")

            core = Mock()
            core.issue_service.get_issue.side_effect = Exception("DB error")

            # Should not raise
            result = FolderStructureValidator.scan_for_folder_structure_issues(
                issues_dir, core
            )

            assert result == {}

    def test_scan_result_structure_misplaced(self):
        """Test structure of misplaced issue result."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            (issues_dir / "a1b2c3d4-Issue.md").write_text("# Issue")
            (issues_dir / "v1.0").mkdir()

            mock_issue = Mock()
            mock_issue.id = "a1b2c3d4"
            mock_issue.title = "Test Issue"
            mock_issue.milestone = "v1.0"

            core = Mock()
            core.issue_service.get_issue.return_value = mock_issue

            result = FolderStructureValidator.scan_for_folder_structure_issues(
                issues_dir, core
            )

            misplaced = result["misplaced"][0]
            assert "issue_id" in misplaced
            assert "title" in misplaced
            assert "current_location" in misplaced
            assert "assigned_milestone" in misplaced
            assert "expected_location" in misplaced

    def test_scan_result_structure_orphaned(self):
        """Test structure of orphaned issue result."""
        with TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            v1_dir = issues_dir / "v1.0"
            v1_dir.mkdir()
            (v1_dir / "a1b2c3d4-Issue.md").write_text("# Issue")

            mock_issue = Mock()
            mock_issue.id = "a1b2c3d4"
            mock_issue.title = "Test Issue"
            mock_issue.milestone = None

            core = Mock()
            core.issue_service.get_issue.return_value = mock_issue

            result = FolderStructureValidator.scan_for_folder_structure_issues(
                issues_dir, core
            )

            orphaned = result["orphaned"][0]
            assert "issue_id" in orphaned
            assert "title" in orphaned
            assert "location" in orphaned
            assert "folder" in orphaned
