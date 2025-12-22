"""Tests for archivable issues validator."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from roadmap.core.services.base_validator import HealthStatus
from roadmap.core.services.validators.archivable_issues_validator import (
    ArchivableIssuesValidator,
)


class TestArchivableIssuesValidator:
    """Test ArchivableIssuesValidator."""

    @pytest.fixture
    def mock_core(self):
        """Create mock core with issue service."""
        core = MagicMock()
        core.issue_service = MagicMock()
        return core

    def test_scan_for_archivable_issues_empty_list(self, mock_core):
        """Test scan with no issues."""
        mock_core.issue_service.list_issues.return_value = []
        result = ArchivableIssuesValidator.scan_for_archivable_issues(mock_core)
        assert result == []

    def test_scan_for_archivable_issues_open_issues(self, mock_core):
        """Test scan ignores open issues."""
        issue = MagicMock()
        issue.status.value = "open"
        issue.actual_end_date = None
        mock_core.issue_service.list_issues.return_value = [issue]

        result = ArchivableIssuesValidator.scan_for_archivable_issues(mock_core)
        assert result == []

    def test_scan_for_archivable_issues_recently_closed(self, mock_core):
        """Test scan ignores recently closed issues."""
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)

        issue = MagicMock()
        issue.status.value = "closed"
        issue.actual_end_date = yesterday
        issue.id = "ISSUE-1"
        issue.title = "Test Issue"
        mock_core.issue_service.list_issues.return_value = [issue]

        with patch(
            "roadmap.core.services.validators.archivable_issues_validator.now_utc",
            return_value=now,
        ):
            result = ArchivableIssuesValidator.scan_for_archivable_issues(
                mock_core, threshold_days=30
            )
        assert result == []

    def test_scan_for_archivable_issues_old_closed_issues(self, mock_core):
        """Test scan finds issues closed beyond threshold."""
        now = datetime.utcnow()
        old_date = now - timedelta(days=40)

        issue = MagicMock()
        issue.status.value = "closed"
        issue.actual_end_date = old_date
        issue.id = "ISSUE-1"
        issue.title = "Old Closed Issue"
        mock_core.issue_service.list_issues.return_value = [issue]

        with patch(
            "roadmap.core.services.validators.archivable_issues_validator.now_utc",
            return_value=now,
        ):
            result = ArchivableIssuesValidator.scan_for_archivable_issues(
                mock_core, threshold_days=30
            )

        assert len(result) == 1
        assert result[0]["id"] == "ISSUE-1"
        assert result[0]["title"] == "Old Closed Issue"
        assert result[0]["status"] == "closed"
        assert result[0]["days_since_close"] == 40

    def test_scan_for_archivable_issues_custom_threshold(self, mock_core):
        """Test scan respects custom threshold."""
        now = datetime.utcnow()
        old_date = now - timedelta(days=50)

        issue = MagicMock()
        issue.status.value = "open"
        issue.actual_end_date = old_date
        issue.id = "ISSUE-1"
        issue.title = "Issue with old end date"
        mock_core.issue_service.list_issues.return_value = [issue]

        with patch(
            "roadmap.core.services.validators.archivable_issues_validator.now_utc",
            return_value=now,
        ):
            result = ArchivableIssuesValidator.scan_for_archivable_issues(
                mock_core, threshold_days=60
            )

        assert len(result) == 0  # 50 days < 60 day threshold

    def test_scan_for_archivable_issues_exception_handling(self, mock_core):
        """Test scan handles exceptions gracefully."""
        mock_core.issue_service.list_issues.side_effect = Exception("DB Error")

        result = ArchivableIssuesValidator.scan_for_archivable_issues(mock_core)
        assert result == []

    def test_scan_for_archivable_issues_multiple_issues(self, mock_core):
        """Test scan finds multiple archivable issues."""
        now = datetime.utcnow()
        old_date_1 = now - timedelta(days=35)
        old_date_2 = now - timedelta(days=45)
        recent_date = now - timedelta(days=5)

        issues = []
        for i, date in enumerate([old_date_1, old_date_2, recent_date], 1):
            issue = MagicMock()
            issue.status.value = "closed"
            issue.actual_end_date = date
            issue.id = f"ISSUE-{i}"
            issue.title = f"Issue {i}"
            issues.append(issue)

        mock_core.issue_service.list_issues.return_value = issues

        with patch(
            "roadmap.core.services.validators.archivable_issues_validator.now_utc",
            return_value=now,
        ):
            result = ArchivableIssuesValidator.scan_for_archivable_issues(
                mock_core, threshold_days=30
            )

        assert len(result) == 2
        assert result[0]["id"] == "ISSUE-1"
        assert result[1]["id"] == "ISSUE-2"

    def test_check_archivable_issues_no_issues(self, mock_core):
        """Test check when no archivable issues found."""
        with patch(
            "roadmap.core.services.validators.archivable_issues_validator.ArchivableIssuesValidator.scan_for_archivable_issues",
            return_value=[],
        ):
            status, message = ArchivableIssuesValidator.check_archivable_issues(
                mock_core
            )
            assert status == HealthStatus.HEALTHY
            assert "No issues to archive" in message

    def test_check_archivable_issues_found(self, mock_core):
        """Test check when archivable issues are found."""
        archivable = [
            {
                "id": "ISSUE-1",
                "title": "Old Issue",
                "status": "closed",
                "closed_date": "2024-01-01",
                "days_since_close": 40,
            }
        ]
        with patch(
            "roadmap.core.services.validators.archivable_issues_validator.ArchivableIssuesValidator.scan_for_archivable_issues",
            return_value=archivable,
        ):
            status, message = ArchivableIssuesValidator.check_archivable_issues(
                mock_core
            )
            assert status == HealthStatus.DEGRADED
            assert "archiv" in message.lower()

    def test_check_archivable_issues_exception(self, mock_core):
        """Test check handles exceptions gracefully."""
        with patch(
            "roadmap.core.services.validators.archivable_issues_validator.ArchivableIssuesValidator.scan_for_archivable_issues",
            side_effect=Exception("Error"),
        ):
            status, message = ArchivableIssuesValidator.check_archivable_issues(
                mock_core
            )
            assert status == HealthStatus.HEALTHY
