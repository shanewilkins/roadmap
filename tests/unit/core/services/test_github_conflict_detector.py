"""Tests for GitHub conflict detector service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from roadmap.common.constants import Priority, Status
from roadmap.core.domain.issue import Issue
from roadmap.core.services.github_conflict_detector import GitHubConflictDetector


class TestGitHubConflictDetector:
    """Tests for GitHubConflictDetector."""

    @pytest.fixture
    def mock_integration_service(self):
        """Create mock integration service."""
        service = Mock()
        service.get_github_config.return_value = ("fake_token", "owner", "repo")
        return service

    @pytest.fixture
    def detector(self, mock_integration_service):
        """Create detector instance."""
        return GitHubConflictDetector(mock_integration_service)

    @pytest.fixture
    def sample_issue(self):
        """Create sample issue."""
        return Issue(
            id="abc123",
            title="Test Issue",
            priority=Priority.HIGH,
            status=Status.IN_PROGRESS,
            remote_ids={"github": 42},
        )

    def test_init_creates_detector(self, mock_integration_service):
        """Test initializing detector sets up client and config."""
        detector = GitHubConflictDetector(mock_integration_service)

        assert detector.service == mock_integration_service
        assert detector.owner == "owner"
        assert detector.repo == "repo"
        assert detector.client is not None

    def test_detect_conflicts_no_sync_history(self, detector, sample_issue):
        """Test detecting conflicts with no sync history."""
        sample_issue.github_sync_metadata = None
        sample_issue.updated = None

        conflicts = detector.detect_conflicts(sample_issue, 42)

        assert conflicts["has_conflicts"] is False
        assert conflicts["local_modified"] is False
        assert conflicts["github_modified"] is False
        assert conflicts["last_sync"] is None
        assert len(conflicts["warnings"]) == 1
        assert "No sync history available" in conflicts["warnings"][0]

    def test_detect_conflicts_no_github_config(
        self, mock_integration_service, sample_issue
    ):
        """Test detecting conflicts with no GitHub config."""
        mock_integration_service.get_github_config.return_value = (
            "fake_token",
            None,
            None,
        )
        detector = GitHubConflictDetector(mock_integration_service)

        now = datetime.now(UTC)
        sample_issue.github_sync_metadata = {"sync_timestamp": now}

        conflicts = detector.detect_conflicts(sample_issue, 42)

        assert conflicts["has_conflicts"] is False
        assert any(
            "GitHub configuration missing" in warning
            for warning in conflicts["warnings"]
        )

    def test_detect_conflicts_only_local_modified(self, detector, sample_issue):
        """Test detecting when only local issue was modified."""
        now = datetime.now(UTC)
        sync_time = now - timedelta(hours=2)

        sample_issue.github_sync_metadata = {"sync_timestamp": sync_time}
        sample_issue.updated = now

        with patch.object(detector.client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = {"updated_at": sync_time.isoformat() + "Z"}

            conflicts = detector.detect_conflicts(sample_issue, 42)

        assert conflicts["has_conflicts"] is False
        assert conflicts["local_modified"] is True
        assert conflicts["github_modified"] is False
        assert "Local issue was modified after last sync" in conflicts["warnings"]

    def test_detect_conflicts_only_github_modified(self, detector, sample_issue):
        """Test detecting when only GitHub issue was modified."""
        now = datetime.now(UTC)
        sync_time = now - timedelta(hours=2)
        github_update = now - timedelta(minutes=30)

        sample_issue.github_sync_metadata = {"sync_timestamp": sync_time}
        sample_issue.updated = sync_time

        with patch.object(detector.client, "fetch_issue") as mock_fetch:
            with patch(
                "roadmap.common.datetime_parser.UnifiedDateTimeParser.parse_github_timestamp"
            ) as mock_parse:
                mock_parse.return_value = github_update
                mock_fetch.return_value = {
                    "updated_at": github_update.isoformat() + "Z"
                }

                conflicts = detector.detect_conflicts(sample_issue, 42)

        assert conflicts["has_conflicts"] is False
        assert conflicts["local_modified"] is False
        assert conflicts["github_modified"] is True
        assert "GitHub issue was modified after last sync" in conflicts["warnings"]

    def test_detect_conflicts_both_modified(self, detector, sample_issue):
        """Test detecting when both local and GitHub were modified."""
        now = datetime.now(UTC)
        sync_time = now - timedelta(hours=2)

        sample_issue.github_sync_metadata = {"sync_timestamp": sync_time}
        sample_issue.updated = now

        with patch.object(detector.client, "fetch_issue") as mock_fetch:
            with patch(
                "roadmap.common.datetime_parser.UnifiedDateTimeParser.parse_github_timestamp"
            ) as mock_parse:
                mock_parse.return_value = now
                mock_fetch.return_value = {"updated_at": now.isoformat() + "Z"}

                conflicts = detector.detect_conflicts(sample_issue, 42)

        assert conflicts["has_conflicts"] is True
        assert conflicts["local_modified"] is True
        assert conflicts["github_modified"] is True
        assert any(
            "Both local and GitHub versions have changes" in w
            for w in conflicts["warnings"]
        )
        assert any(
            "Review carefully before syncing" in w for w in conflicts["warnings"]
        )

    def test_detect_conflicts_no_modifications(self, detector, sample_issue):
        """Test detecting when neither was modified."""
        now = datetime.now(UTC)
        sync_time = now - timedelta(hours=2)

        sample_issue.github_sync_metadata = {"sync_timestamp": sync_time}
        sample_issue.updated = sync_time

        with patch.object(detector.client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = {"updated_at": sync_time.isoformat() + "Z"}

            conflicts = detector.detect_conflicts(sample_issue, 42)

        assert conflicts["has_conflicts"] is False
        assert conflicts["local_modified"] is False
        assert conflicts["github_modified"] is False

    def test_detect_conflicts_github_fetch_error(self, detector, sample_issue):
        """Test handling GitHub fetch errors gracefully."""
        now = datetime.now(UTC)
        sync_time = now - timedelta(hours=2)

        sample_issue.github_sync_metadata = {"sync_timestamp": sync_time}
        sample_issue.updated = sync_time

        with patch.object(detector.client, "fetch_issue") as mock_fetch:
            mock_fetch.side_effect = Exception("Network error")

            conflicts = detector.detect_conflicts(sample_issue, 42)

        assert conflicts["has_conflicts"] is False
        assert "Could not check GitHub for changes" in conflicts["warnings"][0]

    def test_detect_conflicts_invalid_github_timestamp(self, detector, sample_issue):
        """Test handling invalid GitHub timestamps."""
        now = datetime.now(UTC)
        sync_time = now - timedelta(hours=2)

        sample_issue.github_sync_metadata = {"sync_timestamp": sync_time}
        sample_issue.updated = sync_time

        with patch.object(detector.client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = {"updated_at": None}

            conflicts = detector.detect_conflicts(sample_issue, 42)

        assert conflicts["has_conflicts"] is False
        assert conflicts["github_modified"] is False

    def test_detect_conflicts_uses_updated_at_as_fallback(self, detector, sample_issue):
        """Test using issue.updated as fallback for sync time."""
        now = datetime.now(UTC)

        sample_issue.github_sync_metadata = None
        sample_issue.updated = now

        with patch.object(detector.client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = {
                "updated_at": (now - timedelta(hours=1)).isoformat() + "Z"
            }

            conflicts = detector.detect_conflicts(sample_issue, 42)

        # Should use updated_at as sync time
        assert conflicts["last_sync"] == now

    def test_get_last_sync_time_from_metadata(self, detector, sample_issue):
        """Test extracting sync time from metadata."""
        now = datetime.now(UTC)
        sample_issue.github_sync_metadata = {"sync_timestamp": now}

        sync_time = detector._get_last_sync_time(sample_issue)

        assert sync_time == now

    def test_get_last_sync_time_fallback_to_updated(self, detector, sample_issue):
        """Test falling back to issue.updated for sync time."""
        now = datetime.now(UTC)
        sample_issue.github_sync_metadata = None
        sample_issue.updated = now

        sync_time = detector._get_last_sync_time(sample_issue)

        assert sync_time == now

    def test_get_last_sync_time_no_data(self, detector, sample_issue):
        """Test when no sync time data available."""
        sample_issue.github_sync_metadata = None
        sample_issue.updated = None

        sync_time = detector._get_last_sync_time(sample_issue)

        assert sync_time is None

    @pytest.mark.parametrize(
        "updated,sync_time,expected",
        [
            ("now", "past", True),
            ("now", "now", False),
            ("past", "now", False),
            (None, "now", False),
        ],
    )
    def test_is_local_modified_after_sync(self, detector, updated, sync_time, expected):
        """Test checking if local issue was modified after sync."""
        base_time = datetime.now(UTC)

        if updated == "now":
            issue_updated = base_time
        elif updated == "past":
            issue_updated = base_time - timedelta(hours=1)
        else:
            issue_updated = None

        if sync_time == "now":
            last_sync = base_time
        else:
            last_sync = base_time - timedelta(hours=1)

        issue = Issue(id="test", title="Test")
        issue.updated = issue_updated  # type: ignore

        result = detector._is_local_modified_after_sync(issue, last_sync)

        assert result == expected

    def test_parse_github_timestamp_valid(self, detector):
        """Test parsing valid GitHub timestamp."""
        timestamp = "2024-01-15T12:30:45Z"

        with patch(
            "roadmap.common.datetime_parser.UnifiedDateTimeParser.parse_github_timestamp"
        ) as mock_parse:
            mock_parse.return_value = datetime(2024, 1, 15, 12, 30, 45)

            result = detector._parse_github_timestamp(timestamp)

        assert result == datetime(2024, 1, 15, 12, 30, 45)
        mock_parse.assert_called_once_with(timestamp)

    def test_parse_github_timestamp_none(self, detector):
        """Test parsing None timestamp."""
        result = detector._parse_github_timestamp(None)

        assert result is None

    def test_parse_github_timestamp_invalid(self, detector):
        """Test parsing invalid timestamp."""
        with patch(
            "roadmap.common.datetime_parser.UnifiedDateTimeParser.parse_github_timestamp"
        ) as mock_parse:
            mock_parse.side_effect = ValueError("Invalid timestamp")

            result = detector._parse_github_timestamp("invalid")

        assert result is None

    def test_parse_github_timestamp_attribute_error(self, detector):
        """Test parsing with AttributeError."""
        with patch(
            "roadmap.common.datetime_parser.UnifiedDateTimeParser.parse_github_timestamp"
        ) as mock_parse:
            mock_parse.side_effect = AttributeError("Missing attribute")

            result = detector._parse_github_timestamp("bad")

        assert result is None

    def test_get_conflict_summary_no_conflicts(self, detector):
        """Test summary for no conflicts."""
        conflicts = {
            "has_conflicts": False,
            "warnings": [],
        }

        summary = detector.get_conflict_summary(conflicts)

        assert "No conflicts detected" in summary
        assert "Safe to sync" in summary

    def test_get_conflict_summary_with_warnings(self, detector):
        """Test summary with warnings."""
        conflicts = {
            "has_conflicts": False,
            "warnings": [
                "GitHub issue was modified after last sync",
                "Local issue was modified after last sync",
            ],
        }

        summary = detector.get_conflict_summary(conflicts)

        assert "Conflict Detection Summary" in summary
        assert "• GitHub issue was modified after last sync" in summary
        assert "• Local issue was modified after last sync" in summary

    def test_get_conflict_summary_with_actual_conflicts(self, detector):
        """Test summary when has_conflicts is True."""
        conflicts = {
            "has_conflicts": True,
            "warnings": [
                "⚠️  Both local and GitHub versions have changes. Review carefully before syncing."
            ],
        }

        summary = detector.get_conflict_summary(conflicts)

        assert "Conflict Detection Summary" in summary
        assert "Review changes manually before syncing" in summary

    def test_conflict_detection_workflow(self, detector, sample_issue):
        """Test complete conflict detection workflow."""
        now = datetime.now(UTC)
        sync_time = now - timedelta(hours=1)
        github_update = now + timedelta(minutes=30)

        sample_issue.github_sync_metadata = {"sync_timestamp": sync_time}
        sample_issue.updated = now

        with patch.object(detector.client, "fetch_issue") as mock_fetch:
            with patch(
                "roadmap.common.datetime_parser.UnifiedDateTimeParser.parse_github_timestamp"
            ) as mock_parse:
                mock_parse.return_value = github_update
                mock_fetch.return_value = {
                    "updated_at": github_update.isoformat() + "Z"
                }

                conflicts = detector.detect_conflicts(sample_issue, 42)
                summary = detector.get_conflict_summary(conflicts)

        assert conflicts["has_conflicts"] is True
        assert len(conflicts["warnings"]) >= 2
        assert "Review changes manually" in summary

    @pytest.mark.parametrize(
        "github_updated_str,expected_modified",
        [
            ("2024-01-15T14:00:00Z", True),
            ("2024-01-15T10:00:00Z", False),
        ],
    )
    def test_detect_conflicts_timestamp_comparison(
        self, detector, sample_issue, github_updated_str, expected_modified
    ):
        """Test timestamp comparison for conflict detection."""
        sync_time = datetime(2024, 1, 15, 12, 0, 0)
        sample_issue.github_sync_metadata = {"sync_timestamp": sync_time}
        sample_issue.updated = sync_time

        with patch.object(detector.client, "fetch_issue") as mock_fetch:
            with patch(
                "roadmap.common.datetime_parser.UnifiedDateTimeParser.parse_github_timestamp"
            ) as mock_parse:
                if expected_modified:
                    mock_parse.return_value = datetime(2024, 1, 15, 14, 0, 0)
                else:
                    mock_parse.return_value = datetime(2024, 1, 15, 10, 0, 0)

                mock_fetch.return_value = {"updated_at": github_updated_str}

                conflicts = detector.detect_conflicts(sample_issue, 42)

        assert conflicts["github_modified"] == expected_modified

    def test_detect_conflicts_with_multiple_sync_metadata_keys(
        self, detector, sample_issue
    ):
        """Test conflict detection with complete sync metadata."""
        now = datetime.now(UTC)
        sample_issue.github_sync_metadata = {
            "sync_timestamp": now - timedelta(hours=1),
            "sync_count": 5,
            "last_sync_status": "success",
        }
        sample_issue.updated = now

        with patch.object(detector.client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = {
                "updated_at": (now - timedelta(hours=2)).isoformat() + "Z"
            }

            conflicts = detector.detect_conflicts(sample_issue, 42)

        assert conflicts["local_modified"] is True
        assert conflicts["github_modified"] is False
        assert conflicts["has_conflicts"] is False
