"""High-quality test suite for SyncMetadataService.

Tests focus on:
- Metadata record management
- Sync history tracking
- Success rate calculations
- Statistics aggregation
- Serialization/deserialization
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from roadmap.core.domain.issue import Issue
from roadmap.core.services.sync.sync_metadata_service import (
    SyncMetadata,
    SyncMetadataService,
    SyncRecord,
)


class TestSyncRecord:
    """Tests for SyncRecord dataclass."""

    def test_sync_record_creation_success(self):
        """Create successful sync record."""
        now = datetime.now(UTC).isoformat()
        record = SyncRecord(
            sync_timestamp=now,
            success=True,
            local_changes={"status": "open"},
            github_changes=None,
            conflict_resolution=None,
            error_message=None,
        )

        assert record.sync_timestamp == now
        assert record.success is True
        assert record.local_changes == {"status": "open"}

    def test_sync_record_creation_with_error(self):
        """Create failed sync record with error."""
        now = datetime.now(UTC).isoformat()
        record = SyncRecord(
            sync_timestamp=now,
            success=False,
            error_message="Connection timeout",
        )

        assert record.success is False
        assert record.error_message == "Connection timeout"


class TestSyncMetadata:
    """Tests for SyncMetadata dataclass."""

    def test_sync_metadata_creation(self):
        """Create sync metadata."""
        metadata = SyncMetadata(
            issue_id="issue-123",
            github_issue_id=456,
        )

        assert metadata.issue_id == "issue-123"
        assert metadata.github_issue_id == 456
        assert metadata.sync_count == 0
        assert metadata.successful_syncs == 0

    def test_add_sync_record_success(self):
        """Add successful sync record."""
        metadata = SyncMetadata(
            issue_id="issue-123",
            github_issue_id=456,
        )

        now = datetime.now(UTC).isoformat()
        record = SyncRecord(
            sync_timestamp=now,
            success=True,
        )

        metadata.add_sync_record(record)

        assert metadata.sync_count == 1
        assert metadata.successful_syncs == 1
        assert metadata.last_sync_status == "success"

    def test_add_sync_record_with_conflict(self):
        """Add sync record with conflict resolution."""
        metadata = SyncMetadata(
            issue_id="issue-123",
            github_issue_id=456,
        )

        now = datetime.now(UTC).isoformat()
        record = SyncRecord(
            sync_timestamp=now,
            success=False,
            conflict_resolution="local",
        )

        metadata.add_sync_record(record)

        assert metadata.last_sync_status == "conflict"

    def test_add_sync_record_error(self):
        """Add failed sync record."""
        metadata = SyncMetadata(
            issue_id="issue-123",
            github_issue_id=456,
        )

        now = datetime.now(UTC).isoformat()
        record = SyncRecord(
            sync_timestamp=now,
            success=False,
            error_message="API error",
        )

        metadata.add_sync_record(record)

        assert metadata.last_sync_status == "error"

    def test_get_success_rate_no_syncs(self):
        """Get success rate with no syncs."""
        metadata = SyncMetadata(
            issue_id="issue-123",
            github_issue_id=456,
        )

        rate = metadata.get_success_rate()

        assert rate == 0.0

    def test_get_success_rate_all_successful(self):
        """Get success rate with all successful syncs."""
        metadata = SyncMetadata(
            issue_id="issue-123",
            github_issue_id=456,
        )

        for _ in range(5):
            now = datetime.now(UTC).isoformat()
            record = SyncRecord(sync_timestamp=now, success=True)
            metadata.add_sync_record(record)

        rate = metadata.get_success_rate()

        assert rate == 100.0

    def test_get_success_rate_partial_success(self):
        """Get success rate with partial success."""
        metadata = SyncMetadata(
            issue_id="issue-123",
            github_issue_id=456,
        )

        # 3 successful
        for _ in range(3):
            now = datetime.now(UTC).isoformat()
            record = SyncRecord(sync_timestamp=now, success=True)
            metadata.add_sync_record(record)

        # 2 failed
        for _ in range(2):
            now = datetime.now(UTC).isoformat()
            record = SyncRecord(sync_timestamp=now, success=False)
            metadata.add_sync_record(record)

        rate = metadata.get_success_rate()

        assert rate == 60.0

    def test_to_dict(self):
        """Convert metadata to dict."""
        metadata = SyncMetadata(
            issue_id="issue-123",
            github_issue_id=456,
        )

        now = datetime.now(UTC).isoformat()
        record = SyncRecord(sync_timestamp=now, success=True)
        metadata.add_sync_record(record)

        data = metadata.to_dict()

        assert data["issue_id"] == "issue-123"
        assert data["github_issue_id"] == 456
        assert data["sync_count"] == 1
        assert len(data["sync_history"]) == 1

    def test_from_dict(self):
        """Create metadata from dict."""
        data = {
            "issue_id": "issue-123",
            "github_issue_id": 456,
            "sync_count": 2,
            "successful_syncs": 1,
            "last_sync_status": "success",
            "sync_history": [
                {
                    "sync_timestamp": datetime.now(UTC).isoformat(),
                    "success": True,
                    "local_changes": None,
                    "github_changes": None,
                    "conflict_resolution": None,
                    "error_message": None,
                }
            ],
        }

        metadata = SyncMetadata.from_dict(data)

        assert metadata.issue_id == "issue-123"
        assert metadata.sync_count == 2
        assert len(metadata.sync_history) == 1


class TestSyncMetadataService:
    """Tests for SyncMetadataService."""

    def test_sync_metadata_service_init(self):
        """Initialize metadata service."""
        mock_core = MagicMock()
        service = SyncMetadataService(mock_core)

        assert service._cache == {}
        assert service.core == mock_core

    def test_get_metadata_creates_new(self):
        """Get metadata creates new metadata."""
        mock_core = MagicMock()

        service = SyncMetadataService(mock_core)

        issue = MagicMock(spec=Issue)
        issue.id = "issue-123"
        issue.github_issue = 456
        issue.github_sync_metadata = None

        metadata = service.get_metadata(issue)

        assert metadata.issue_id == "issue-123"
        assert metadata.github_issue_id == 456

    def test_get_metadata_loads_from_cache(self):
        """Get metadata uses cache."""
        mock_core = MagicMock()

        service = SyncMetadataService(mock_core)

        issue = MagicMock(spec=Issue)
        issue.id = "issue-123"
        issue.github_issue = 456
        issue.github_sync_metadata = None

        metadata1 = service.get_metadata(issue)
        metadata2 = service.get_metadata(issue)

        # Should be same object
        assert metadata1 is metadata2

    def test_record_sync(self):
        """Record sync operation."""
        mock_core = MagicMock()

        service = SyncMetadataService(mock_core)

        issue = MagicMock(spec=Issue)
        issue.id = "issue-123"
        issue.github_issue = 456

        service.record_sync(
            issue,
            success=True,
            local_changes={"status": "open"},
        )

        metadata = service.get_metadata(issue)
        assert metadata.sync_count == 1
        assert metadata.successful_syncs == 1

    def test_get_sync_history(self):
        """Get sync history for issue."""
        mock_core = MagicMock()

        service = SyncMetadataService(mock_core)

        issue = MagicMock(spec=Issue)
        issue.id = "issue-123"
        issue.github_issue = 456

        # Record multiple syncs
        for i in range(3):
            service.record_sync(issue, success=i % 2 == 0)

        history = service.get_sync_history(issue, limit=2)

        assert len(history) == 2

    def test_get_statistics_empty_issues(self):
        """Get statistics with empty issues."""
        mock_core = MagicMock()

        service = SyncMetadataService(mock_core)

        stats = service.get_statistics([])

        assert stats["total_issues"] == 0
        assert stats["never_synced"] == 0
        assert stats["total_sync_attempts"] == 0

    def test_get_statistics_with_issues(self):
        """Get statistics with issues."""
        mock_core = MagicMock()

        service = SyncMetadataService(mock_core)

        issues = []
        for i in range(3):
            issue = MagicMock(spec=Issue)
            issue.id = f"issue-{i}"
            issue.github_issue = i
            issues.append(issue)

        # Record syncs
        service.record_sync(issues[0], success=True)
        service.record_sync(issues[0], success=True)
        service.record_sync(issues[1], success=False)

        stats = service.get_statistics(issues)

        assert stats["total_issues"] == 3
        assert stats["never_synced"] == 1
        assert stats["total_sync_attempts"] == 3

    def test_get_statistics_success_rate(self):
        """Get statistics calculates success rate."""
        mock_core = MagicMock()

        service = SyncMetadataService(mock_core)

        issue = MagicMock(spec=Issue)
        issue.id = "issue-1"
        issue.github_issue = 1

        # 3 successful, 1 failed
        service.record_sync(issue, success=True)
        service.record_sync(issue, success=True)
        service.record_sync(issue, success=True)
        service.record_sync(issue, success=False)

        stats = service.get_statistics([issue])

        assert stats["success_rate"] == 75.0

    def test_record_sync_with_conflict(self):
        """Record sync with conflict resolution."""
        mock_core = MagicMock()

        service = SyncMetadataService(mock_core)

        issue = MagicMock(spec=Issue)
        issue.id = "issue-123"
        issue.github_issue = 456

        service.record_sync(
            issue,
            success=False,
            conflict_resolution="local",
        )

        stats = service.get_statistics([issue])
        assert stats["total_conflicts"] == 1
