"""Tests for orphaned issues validator."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.core.services.base_validator import HealthStatus
from roadmap.core.services.validators.orphaned_issues_validator import (
    OrphanedIssuesValidator,
)
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestOrphanedIssuesValidator:
    """Test OrphanedIssuesValidator."""

    @pytest.fixture
    def mock_core(self, mock_core_initialized):
        """Create mock core with issue service.

        Uses centralized mock_core_initialized and adds service-specific setup.
        """
        mock_core_initialized.issue_service = TestDataFactory.create_mock_core(
            is_initialized=True
        )
        return mock_core_initialized

    def test_scan_for_orphaned_issues_empty_list(self, mock_core):
        """Test scan with no issues."""
        with patch("roadmap.core.services.validators.orphaned_issues_validator.Path"):
            mock_core.issues.list.return_value = []
            result = OrphanedIssuesValidator.scan_for_orphaned_issues(mock_core)
            assert result == []

    def test_scan_for_orphaned_issues_directory_not_exists(self, mock_core):
        """Test scan when .roadmap directory doesn't exist."""
        with patch(
            "roadmap.core.services.validators.orphaned_issues_validator.Path"
        ) as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            mock_dir.resolve.return_value = mock_dir
            mock_path.return_value = mock_dir

            mock_core.issues.list.return_value = []

            result = OrphanedIssuesValidator.scan_for_orphaned_issues(mock_core)
            assert result == []

    def test_scan_for_orphaned_issues_all_assigned(self, mock_core):
        """Test scan with all issues assigned to milestones."""
        with patch("roadmap.core.services.validators.orphaned_issues_validator.Path"):
            issue1 = MagicMock()
            issue1.id = "ISSUE-1"
            issue1.title = "Test Issue 1"
            issue1.milestone = "Q1-2024"
            issue1.status = "OPEN"

            issue2 = MagicMock()
            issue2.id = "ISSUE-2"
            issue2.title = "Test Issue 2"
            issue2.milestone = "Q2-2024"
            issue2.status = "OPEN"

            mock_core.issues.list.return_value = [issue1, issue2]

            result = OrphanedIssuesValidator.scan_for_orphaned_issues(mock_core)
            assert result == []

    def test_scan_for_orphaned_issues_finds_orphans_with_none(self, mock_core):
        """Test scan finds issues with None milestone."""
        with patch(
            "roadmap.core.services.validators.orphaned_issues_validator.Path"
        ) as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_dir.resolve.return_value = mock_dir
            mock_path.return_value = mock_dir

            issue = MagicMock()
            issue.id = "ISSUE-1"
            issue.title = "Orphaned Issue"
            issue.milestone = None
            issue.status = "OPEN"
            mock_core.issues.list.return_value = [issue]

            # Mock _find_issue_folder to return issues_dir (indicating orphan)
            with patch(
                "roadmap.core.services.validators.orphaned_issues_validator.OrphanedIssuesValidator._find_issue_folder",
                return_value=mock_dir,
            ):
                result = OrphanedIssuesValidator.scan_for_orphaned_issues(mock_core)
                assert len(result) == 1
                assert result[0]["id"] == "ISSUE-1"
                assert result[0]["title"] == "Orphaned Issue"

    def test_scan_for_orphaned_issues_finds_orphans_with_empty_string(self, mock_core):
        """Test scan finds issues with empty string milestone."""
        with patch(
            "roadmap.core.services.validators.orphaned_issues_validator.Path"
        ) as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_dir.resolve.return_value = mock_dir
            mock_path.return_value = mock_dir

            issue = MagicMock()
            issue.id = "ISSUE-2"
            issue.title = "Empty Milestone Issue"
            issue.milestone = ""
            issue.status = "OPEN"
            mock_core.issues.list.return_value = [issue]

            # Mock _find_issue_folder to return issues_dir (indicating orphan)
            with patch(
                "roadmap.core.services.validators.orphaned_issues_validator.OrphanedIssuesValidator._find_issue_folder",
                return_value=mock_dir,
            ):
                result = OrphanedIssuesValidator.scan_for_orphaned_issues(mock_core)
                assert len(result) == 1
                assert result[0]["id"] == "ISSUE-2"

    def test_scan_for_orphaned_issues_mixed(self, mock_core):
        """Test scan with mix of orphaned and assigned issues."""
        with patch(
            "roadmap.core.services.validators.orphaned_issues_validator.Path"
        ) as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_dir.resolve.return_value = mock_dir
            mock_path.return_value = mock_dir

            issues = []
            for i, milestone in enumerate(["Q1-2024", None, "", "Q2-2024"], 1):
                issue = MagicMock()
                issue.id = f"ISSUE-{i}"
                issue.title = f"Issue {i}"
                issue.milestone = milestone
                issue.status = "OPEN"
                issues.append(issue)

            mock_core.issues.list.return_value = issues

            # Mock _find_issue_folder to return issues_dir for ISSUE-2 and ISSUE-3
            def mock_find_folder(issue_id, issues_dir, archive_dir):
                if issue_id in ["ISSUE-2", "ISSUE-3"]:
                    return issues_dir  # Orphaned
                return None  # Not found (shouldn't be in results)

            with patch(
                "roadmap.core.services.validators.orphaned_issues_validator.OrphanedIssuesValidator._find_issue_folder",
                side_effect=mock_find_folder,
            ):
                result = OrphanedIssuesValidator.scan_for_orphaned_issues(mock_core)
                assert len(result) == 2
                assert result[0]["id"] == "ISSUE-2"
                assert result[1]["id"] == "ISSUE-3"

    def test_scan_for_orphaned_issues_exception_handling(self, mock_core):
        """Test scan handles exceptions gracefully."""
        mock_core.issues.list.side_effect = Exception("DB Error")

        result = OrphanedIssuesValidator.scan_for_orphaned_issues(mock_core)
        assert result == []

    def test_check_orphaned_issues_no_orphans(self, mock_core):
        """Test check when no orphaned issues found."""
        with patch(
            "roadmap.core.services.validators.orphaned_issues_validator.OrphanedIssuesValidator.scan_for_orphaned_issues",
            return_value=[],
        ):
            status, message = OrphanedIssuesValidator.check_orphaned_issues(mock_core)
            assert status == HealthStatus.HEALTHY
            assert "No orphaned issues found" in message

    def test_check_orphaned_issues_found(self, mock_core):
        """Test check when orphaned issues are found."""
        orphaned = [
            {
                "id": "ISSUE-1",
                "title": "Orphaned Issue",
                "location": "/path/to/ISSUE-1*.md",
            },
            {
                "id": "ISSUE-2",
                "title": "Another Orphan",
                "location": "/path/to/ISSUE-2*.md",
            },
        ]
        with patch(
            "roadmap.core.services.validators.orphaned_issues_validator.OrphanedIssuesValidator.scan_for_orphaned_issues",
            return_value=orphaned,
        ):
            status, message = OrphanedIssuesValidator.check_orphaned_issues(mock_core)
            assert status == HealthStatus.DEGRADED
            assert "2 orphaned issue(s)" in message
            assert "wrong folder" in message.lower()

    def test_check_orphaned_issues_exception(self, mock_core):
        """Test check handles exceptions gracefully."""
        with patch(
            "roadmap.core.services.validators.orphaned_issues_validator.OrphanedIssuesValidator.scan_for_orphaned_issues",
            side_effect=Exception("Error"),
        ):
            status, message = OrphanedIssuesValidator.check_orphaned_issues(mock_core)
            assert status == HealthStatus.HEALTHY
            assert "Could not check" in message
