"""Tests for folder structure validator."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from roadmap.core.services.validators.folder_structure_validator import (
    FolderStructureValidator,
)


class TestProcessMilestoneFile:
    """Tests for _process_milestone_file method."""

    def test_process_milestone_file_orphaned_issue(self, temp_dir_context):
        """Test detecting orphaned issue in milestone folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
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

    def test_process_milestone_file_backup_skipped(self, temp_dir_context):
        """Test that backup files in milestone folders are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
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

    def test_process_milestone_file_with_milestone_assignment(self, temp_dir_context):
        """Test that correctly placed issues are not flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
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

    def test_process_milestone_file_exception_handling(self, temp_dir_context):
        """Test exception handling during file processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
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

    def test_check_milestone_folders_no_folders(self, temp_dir_context):
        """Test when no milestone folders exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            core = Mock()
            orphaned = []

            FolderStructureValidator._check_milestone_folders(
                issues_dir, core, orphaned
            )

            assert orphaned == []

    def test_check_milestone_folders_skips_hidden(self, temp_dir_context):
        """Test that hidden folders are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
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

    def test_check_milestone_folders_skips_backlog(self, temp_dir_context):
        """Test that backlog folder is skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
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

    def test_check_milestone_folders_processes_milestone_files(self, temp_dir_context):
        """Test that milestone folders are processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
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

    def test_check_milestone_folders_multiple_milestones(self, temp_dir_context):
        """Test processing multiple milestone folders."""
        with tempfile.TemporaryDirectory() as tmpdir:
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

    def test_scan_no_issues(self, temp_dir_context):
        """Test scan when no issues are found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            core = Mock()

            result = FolderStructureValidator.scan_for_folder_structure_issues(
                issues_dir, core
            )

            assert result == {}

    def test_scan_finds_misplaced_issues(self, temp_dir_context):
        """Test scan detecting misplaced issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
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

    def test_scan_finds_orphaned_issues(self, temp_dir_context):
        """Test scan detecting orphaned issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
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

    def test_scan_finds_both_types(self, temp_dir_context):
        """Test scan finding both misplaced and orphaned issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
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

    def test_scan_exception_handling(self, temp_dir_context):
        """Test that exceptions during scan are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            (issues_dir / "a1b2c3d4-Issue.md").write_text("# Issue")

            core = Mock()
            core.issue_service.get_issue.side_effect = Exception("DB error")

            # Should not raise
            result = FolderStructureValidator.scan_for_folder_structure_issues(
                issues_dir, core
            )

            assert result == {}

    def test_scan_result_structure_misplaced(self, temp_dir_context):
        """Test structure of misplaced issue result."""
        with tempfile.TemporaryDirectory() as tmpdir:
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

    def test_scan_result_structure_orphaned(self, temp_dir_context):
        """Test structure of orphaned issue result."""
        with tempfile.TemporaryDirectory() as tmpdir:
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
