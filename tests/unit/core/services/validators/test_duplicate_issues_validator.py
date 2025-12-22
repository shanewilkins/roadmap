"""Tests for duplicate issues validator."""

from unittest.mock import MagicMock, patch

from roadmap.core.services.base_validator import HealthStatus
from roadmap.core.services.validators.duplicate_issues_validator import (
    DuplicateIssuesValidator,
)


class TestDuplicateIssuesValidator:
    """Test DuplicateIssuesValidator."""

    def test_get_check_name(self):
        """Test getting check name."""
        assert DuplicateIssuesValidator.get_check_name() == "duplicate_issues"

    def test_scan_for_duplicate_issues_empty_directory(self, tmp_path):
        """Test scan with empty directory."""
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        duplicates = DuplicateIssuesValidator.scan_for_duplicate_issues(issues_dir)
        assert duplicates == {}

    def test_scan_for_duplicate_issues_no_duplicates(self, tmp_path):
        """Test scan with unique issue IDs."""
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        # Issue IDs are 8 hex characters
        (issues_dir / "12345678-Issue-1.md").write_text("content")
        (issues_dir / "87654321-Issue-2.md").write_text("content")
        (issues_dir / "abcdef00-Issue-3.md").write_text("content")

        duplicates = DuplicateIssuesValidator.scan_for_duplicate_issues(issues_dir)
        assert duplicates == {}

    def test_scan_for_duplicate_issues_finds_duplicates(self, tmp_path):
        """Test scan finds duplicate issue IDs."""
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        (issues_dir / "12345678-Issue-1.md").write_text("content 1")
        (issues_dir / "12345678-Issue-1-copy.md").write_text("content 2")
        (issues_dir / "87654321-Issue-2.md").write_text("content 3")

        duplicates = DuplicateIssuesValidator.scan_for_duplicate_issues(issues_dir)
        assert len(duplicates) == 1
        assert "12345678" in duplicates
        assert len(duplicates["12345678"]) == 2

    def test_scan_for_duplicate_issues_skips_backups(self, tmp_path):
        """Test that backup files are skipped."""
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        (issues_dir / "12345678-Issue-1.md").write_text("content")
        (issues_dir / "12345678-Issue-1.backup.md").write_text("backup")

        duplicates = DuplicateIssuesValidator.scan_for_duplicate_issues(issues_dir)
        assert duplicates == {}

    def test_scan_for_duplicate_issues_nested_directories(self, tmp_path):
        """Test scan finds duplicates in nested directories."""
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        (issues_dir / "folder1").mkdir()
        (issues_dir / "folder2").mkdir()
        (issues_dir / "folder1" / "12345678-Issue-1.md").write_text("content 1")
        (issues_dir / "folder2" / "12345678-Issue-1.md").write_text("content 2")

        duplicates = DuplicateIssuesValidator.scan_for_duplicate_issues(issues_dir)
        assert len(duplicates) == 1
        assert len(duplicates["12345678"]) == 2

    def test_scan_for_duplicate_issues_multiple_duplicates(self, tmp_path):
        """Test scan with multiple issues having duplicates."""
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        (issues_dir / "12345678-Issue-1.md").write_text("v1")
        (issues_dir / "12345678-Issue-1-copy.md").write_text("v2")
        (issues_dir / "87654321-Issue-2.md").write_text("v1")
        (issues_dir / "87654321-Issue-2-copy.md").write_text("v2")
        (issues_dir / "abcdef00-Issue-3.md").write_text("unique")

        duplicates = DuplicateIssuesValidator.scan_for_duplicate_issues(issues_dir)
        assert len(duplicates) == 2
        assert "12345678" in duplicates
        assert "87654321" in duplicates
        assert "abcdef00" not in duplicates

    def test_perform_check_directory_not_exists(self):
        """Test perform_check when issues directory doesn't exist."""
        with patch(
            "roadmap.core.services.validators.duplicate_issues_validator.Path"
        ) as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

            status, message = DuplicateIssuesValidator.perform_check()
            assert status == HealthStatus.HEALTHY
            assert "not initialized" in message

    def test_perform_check_no_duplicates(self):
        """Test perform_check with no duplicates found."""
        with (
            patch(
                "roadmap.core.services.validators.duplicate_issues_validator.Path"
            ) as mock_path,
            patch(
                "roadmap.core.services.validators.duplicate_issues_validator.DuplicateIssuesValidator.scan_for_duplicate_issues"
            ) as mock_scan,
        ):
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_path.return_value = mock_dir
            mock_scan.return_value = {}

            status, message = DuplicateIssuesValidator.perform_check()
            assert status == HealthStatus.HEALTHY
            assert "No duplicate issues found" in message

    def test_perform_check_finds_duplicates(self):
        """Test perform_check when duplicates are found."""
        with (
            patch(
                "roadmap.core.services.validators.duplicate_issues_validator.Path"
            ) as mock_path,
            patch(
                "roadmap.core.services.validators.duplicate_issues_validator.DuplicateIssuesValidator.scan_for_duplicate_issues"
            ) as mock_scan,
        ):
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_path.return_value = mock_dir

            # Simulate 3 issue IDs with duplicates
            # ISSUE-1 has 2 copies (1 duplicate), ISSUE-2 has 3 copies (2 duplicates)
            mock_scan.return_value = {
                "ISSUE-1": ["file1", "file2"],  # 1 duplicate
                "ISSUE-2": ["file1", "file2", "file3"],  # 2 duplicates
            }

            status, message = DuplicateIssuesValidator.perform_check()
            assert status == HealthStatus.DEGRADED
            assert "2 issue ID(s) have duplicates" in message
            assert "3 duplicate files total" in message
