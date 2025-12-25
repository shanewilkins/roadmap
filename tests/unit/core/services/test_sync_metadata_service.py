"""Tests for sync metadata service."""

import pytest

from roadmap.core.services.sync_metadata_service import (
    SyncMetadata,
    SyncRecord,
)


class TestSyncRecord:
    """Test SyncRecord dataclass."""

    @pytest.mark.parametrize(
        "success,local_changes,github_changes,conflict_resolution,error_message,expected_fields",
        [
            # Successful sync
            (True, {"status": "done"}, None, None, None, ("success", True)),
            # Conflict sync
            (
                False,
                {"status": "done"},
                {"status": "closed"},
                "local",
                None,
                ("conflict_resolution", "local"),
            ),
            # Error sync
            (
                False,
                None,
                None,
                None,
                "Network error",
                ("error_message", "Network error"),
            ),
        ],
    )
    def test_create_sync_record(
        self,
        success,
        local_changes,
        github_changes,
        conflict_resolution,
        error_message,
        expected_fields,
    ):
        """Test creating sync records with various scenarios."""
        record = SyncRecord(
            sync_timestamp="2025-12-22T10:30:00Z",
            success=success,
            local_changes=local_changes,
            github_changes=github_changes,
            conflict_resolution=conflict_resolution,
            error_message=error_message,
        )
        assert record.sync_timestamp == "2025-12-22T10:30:00Z"
        assert record.success == success
        field_name, expected_value = expected_fields
        assert getattr(record, field_name) == expected_value


class TestSyncMetadata:
    """Test SyncMetadata dataclass."""

    def test_create_new_sync_metadata_ids(self):
        """Test creating new sync metadata stores issue IDs."""
        metadata = SyncMetadata(issue_id="issue-1", github_issue_id=123)
        assert metadata.issue_id == "issue-1"
        assert metadata.github_issue_id == 123

    def test_create_new_sync_metadata_initial_sync_state(self):
        """Test creating new sync metadata has no previous sync."""
        metadata = SyncMetadata(issue_id="issue-1", github_issue_id=123)
        assert metadata.last_sync_time is None
        assert metadata.sync_count == 0
        assert metadata.successful_syncs == 0

    def test_create_new_sync_metadata_initial_status(self):
        """Test creating new sync metadata has never synced status."""
        metadata = SyncMetadata(issue_id="issue-1", github_issue_id=123)
        assert metadata.last_sync_status == "never"

    def test_create_new_sync_metadata_empty_history(self):
        """Test creating new sync metadata has empty sync history."""
        metadata = SyncMetadata(issue_id="issue-1", github_issue_id=123)
        assert metadata.sync_history == []

    @pytest.mark.parametrize(
        "record_success,conflict_resolution,error_message,expected_status,expected_successful",
        [
            # Successful record
            (True, None, None, "success", 1),
            # Conflict record
            (False, "local", None, "conflict", 0),
            # Error record
            (False, None, "Network error", "error", 0),
        ],
    )
    def test_add_sync_record(
        self,
        record_success,
        conflict_resolution,
        error_message,
        expected_status,
        expected_successful,
    ):
        """Test adding sync records with various statuses."""
        metadata = SyncMetadata(issue_id="issue-1", github_issue_id=123)
        record = SyncRecord(
            sync_timestamp="2025-12-22T10:30:00Z",
            success=record_success,
            conflict_resolution=conflict_resolution,
            error_message=error_message,
        )

        metadata.add_sync_record(record)

        assert metadata.sync_count == 1
        assert metadata.successful_syncs == expected_successful
        assert metadata.last_sync_time == "2025-12-22T10:30:00Z"
        assert metadata.last_sync_status == expected_status
        assert len(metadata.sync_history) == 1

    def test_add_multiple_sync_records(self):
        """Test adding multiple sync records."""
        metadata = SyncMetadata(issue_id="issue-1", github_issue_id=123)
        record1 = SyncRecord(sync_timestamp="2025-12-22T10:00:00Z", success=True)
        record2 = SyncRecord(sync_timestamp="2025-12-22T11:00:00Z", success=True)
        record3 = SyncRecord(
            sync_timestamp="2025-12-22T12:00:00Z",
            success=False,
            error_message="Error",
        )

        metadata.add_sync_record(record1)
        metadata.add_sync_record(record2)
        metadata.add_sync_record(record3)

        assert metadata.sync_count == 3
        assert metadata.successful_syncs == 2
        assert metadata.last_sync_time == "2025-12-22T12:00:00Z"
        assert metadata.last_sync_status == "error"

    def test_get_success_rate_no_syncs(self):
        """Test getting success rate with no syncs."""
        metadata = SyncMetadata(issue_id="issue-1", github_issue_id=123)
        assert metadata.get_success_rate() == 0.0

    def test_get_success_rate_all_successful(self):
        """Test getting success rate with all successful syncs."""
        metadata = SyncMetadata(issue_id="issue-1", github_issue_id=123)
        for i in range(5):
            record = SyncRecord(
                sync_timestamp=f"2025-12-22T{10+i}:00:00Z",
                success=True,
            )
            metadata.add_sync_record(record)
        assert metadata.get_success_rate() == 100.0

    def test_get_success_rate_partial(self):
        """Test getting success rate with partial success."""
        metadata = SyncMetadata(issue_id="issue-1", github_issue_id=123)
        record1 = SyncRecord(sync_timestamp="2025-12-22T10:00:00Z", success=True)
        record2 = SyncRecord(sync_timestamp="2025-12-22T11:00:00Z", success=True)
        record3 = SyncRecord(
            sync_timestamp="2025-12-22T12:00:00Z",
            success=False,
            error_message="Error",
        )
        record4 = SyncRecord(sync_timestamp="2025-12-22T13:00:00Z", success=True)

        metadata.add_sync_record(record1)
        metadata.add_sync_record(record2)
        metadata.add_sync_record(record3)
        metadata.add_sync_record(record4)

        assert metadata.get_success_rate() == 75.0

    def test_to_dict(self):
        """Test converting sync metadata to dictionary."""
        metadata = SyncMetadata(
            issue_id="issue-1",
            github_issue_id=123,
        )
        record = SyncRecord(
            sync_timestamp="2025-12-22T10:30:00Z",
            success=True,
            local_changes={"status": "done"},
        )
        metadata.add_sync_record(record)

        result = metadata.to_dict()

        assert result["issue_id"] == "issue-1"
        assert result["github_issue_id"] == 123
        assert result["sync_count"] == 1
        assert result["successful_syncs"] == 1
        assert len(result["sync_history"]) == 1

    def test_from_dict(self):
        """Test creating sync metadata from dictionary."""
        data = {
            "issue_id": "issue-1",
            "github_issue_id": 123,
            "last_sync_time": "2025-12-22T10:30:00Z",
            "sync_count": 2,
            "successful_syncs": 1,
            "last_sync_status": "success",
            "sync_history": [
                {
                    "sync_timestamp": "2025-12-22T10:00:00Z",
                    "success": True,
                    "local_changes": {"status": "done"},
                    "github_changes": None,
                    "conflict_resolution": None,
                    "error_message": None,
                },
                {
                    "sync_timestamp": "2025-12-22T10:30:00Z",
                    "success": False,
                    "local_changes": None,
                    "github_changes": None,
                    "conflict_resolution": None,
                    "error_message": "Network error",
                },
            ],
        }

        metadata = SyncMetadata.from_dict(data)

        assert metadata.issue_id == "issue-1"
        assert metadata.github_issue_id == 123
        assert metadata.sync_count == 2
        assert metadata.successful_syncs == 1
        assert len(metadata.sync_history) == 2

    def test_from_dict_to_dict_roundtrip(self):
        """Test roundtrip conversion from dict to object and back."""
        original_data = {
            "issue_id": "issue-1",
            "github_issue_id": 123,
            "last_sync_time": "2025-12-22T10:30:00Z",
            "sync_count": 1,
            "successful_syncs": 1,
            "last_sync_status": "success",
            "sync_history": [
                {
                    "sync_timestamp": "2025-12-22T10:30:00Z",
                    "success": True,
                    "local_changes": {"status": "done"},
                    "github_changes": None,
                    "conflict_resolution": None,
                    "error_message": None,
                },
            ],
        }

        metadata = SyncMetadata.from_dict(original_data)
        result = metadata.to_dict()

        assert result["issue_id"] == original_data["issue_id"]
        assert result["github_issue_id"] == original_data["github_issue_id"]
        assert result["sync_count"] == original_data["sync_count"]
        assert result["successful_syncs"] == original_data["successful_syncs"]
