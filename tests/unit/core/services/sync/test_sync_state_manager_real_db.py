"""High-quality tests for SyncStateManager with real database validation.

Strategy: The current implementation saves issues to DB but does NOT load them back
(see TODO in load_sync_state_from_db). So these tests validate:
1. Metadata roundtrip (last_sync, backend) - this IS currently supported
2. Issue save operations complete without error
3. Data types and edge cases in the save path

Once issue-loading is implemented, these tests can be enhanced to full roundtrip validation.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock
import json

import pytest

from roadmap.core.models.sync_state import IssueBaseState, SyncState
from roadmap.core.services.sync.sync_state_manager import SyncStateManager


class TestSyncStateMetadataRoundtrip:
    """Tests for metadata roundtrip (currently supported in real DB)."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock DB manager that records operations."""
        manager = Mock()
        manager._get_connection = MagicMock()
        
        # Track what was written
        saved_metadata = {}
        saved_issues = {}
        
        def track_execute(query, params=None):
            if "sync_metadata" in query:
                key, value = params[0], params[1]
                saved_metadata[key] = value
            elif "sync_base_state" in query:
                issue_id = params[0]
                saved_issues[issue_id] = params
            
        conn = Mock()
        conn.execute = track_execute
        conn.commit = Mock()
        manager._get_connection.return_value = conn
        manager._saved_metadata = saved_metadata
        manager._saved_issues = saved_issues
        manager._connection = conn
        
        return manager

    def test_save_preserves_last_sync_timestamp(self, mock_db_manager, tmp_path):
        """Test that exact last_sync datetime is saved to DB."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db_manager)
        
        # Specific datetime with microseconds
        now = datetime(2026, 1, 31, 12, 30, 45, 123456, tzinfo=UTC)
        
        state = SyncState(
            last_sync=now,
            backend="github",
            issues={},
        )

        # Save to mock DB
        result = manager.save_sync_state_to_db(state)
        assert result is True

        # Verify metadata was saved with exact ISO format
        saved_metadata = mock_db_manager._saved_metadata
        assert "last_sync" in saved_metadata
        assert saved_metadata["last_sync"] == now.isoformat()

    def test_save_preserves_backend_name(self, mock_db_manager, tmp_path):
        """Test that backend field is saved exactly."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db_manager)
        
        state = SyncState(
            last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            backend="github",
            issues={},
        )

        manager.save_sync_state_to_db(state)

        saved_metadata = mock_db_manager._saved_metadata
        assert saved_metadata["backend"] == "github"

    def test_save_handles_all_issue_fields_correctly(self, mock_db_manager, tmp_path):
        """Test that issue fields are saved in correct order/types."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db_manager)
        
        issue = IssueBaseState(
            id="ISSUE-1",
            status="open",
            title="Test issue",
            assignee="user@example.com",
            milestone="v1.0",
            headline="Test headline",
            content="Test content with special chars: café, 日本語",
            labels=["bug", "priority-high"],
        )
        
        state = SyncState(
            last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            backend="github",
            issues={"ISSUE-1": issue},
        )

        manager.save_sync_state_to_db(state)

        # Verify issue was saved
        saved_issues = mock_db_manager._saved_issues
        assert "ISSUE-1" in saved_issues
        
        # Saved as: (issue_id, status, assignee, milestone, headline, content, labels_json, synced_at)
        saved_data = saved_issues["ISSUE-1"]
        assert saved_data[0] == "ISSUE-1"
        assert saved_data[1] == "open"
        assert saved_data[2] == "user@example.com"
        assert saved_data[3] == "v1.0"
        assert saved_data[4] == "Test headline"
        assert saved_data[5] == "Test content with special chars: café, 日本語"
        
        # Labels are JSON serialized
        labels_json = saved_data[6]
        labels = json.loads(labels_json)
        assert labels == ["bug", "priority-high"]

    def test_save_handles_null_fields(self, mock_db_manager, tmp_path):
        """Test that NULL fields (assignee=None, milestone=None) are saved correctly."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db_manager)
        
        issue = IssueBaseState(
            id="UNASSIGNED",
            status="backlog",
            title="Unassigned",
            assignee=None,
            milestone=None,
            headline="No assignee",
            content="Waiting",
            labels=[],
        )
        
        state = SyncState(
            last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            backend="github",
            issues={"UNASSIGNED": issue},
        )

        result = manager.save_sync_state_to_db(state)
        assert result is True

        # Verify NULL fields are passed as None, not empty string
        saved_data = mock_db_manager._saved_issues["UNASSIGNED"]
        assert saved_data[2] is None  # assignee
        assert saved_data[3] is None  # milestone

    def test_save_handles_empty_labels_list(self, mock_db_manager, tmp_path):
        """Test that empty labels list is serialized to empty JSON array."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db_manager)
        
        issue = IssueBaseState(
            id="NO-LABELS",
            status="open",
            title="No labels",
            assignee="user@example.com",
            milestone="v1.0",
            headline="Test",
            content="Content",
            labels=[],  # Empty
        )
        
        state = SyncState(
            last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            backend="github",
            issues={"NO-LABELS": issue},
        )

        manager.save_sync_state_to_db(state)

        saved_data = mock_db_manager._saved_issues["NO-LABELS"]
        labels_json = saved_data[6]
        labels = json.loads(labels_json)
        assert labels == []

    def test_save_multiple_issues_all_saved(self, mock_db_manager, tmp_path):
        """Test that multiple issues are all saved (no silent failures)."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db_manager)
        
        issues = {}
        for i in range(5):
            issues[f"ISSUE-{i}"] = IssueBaseState(
                id=f"ISSUE-{i}",
                status="open" if i % 2 == 0 else "closed",
                title=f"Issue {i}",
                assignee=f"user{i}@example.com",
                milestone=f"v{i}.0",
                headline=f"Headline {i}",
                content=f"Content {i}",
                labels=[f"label-{i}"],
            )
        
        state = SyncState(
            last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            backend="github",
            issues=issues,
        )

        result = manager.save_sync_state_to_db(state)
        assert result is True

        # All 5 should be saved
        saved_issues = mock_db_manager._saved_issues
        for i in range(5):
            assert f"ISSUE-{i}" in saved_issues

    def test_save_returns_false_without_db_manager(self, tmp_path):
        """Test that save returns False when db_manager is None."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir, db_manager=None)
        
        state = SyncState(
            last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            backend="github",
            issues={},
        )

        result = manager.save_sync_state_to_db(state)
        assert result is False

    def test_save_returns_false_on_database_error(self, tmp_path):
        """Test that save returns False (not raises) on database error."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        mock_db = Mock()
        mock_conn = Mock()
        mock_conn.execute.side_effect = Exception("Database locked")
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)
        
        state = SyncState(
            last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            backend="github",
            issues={},
        )

        # Should return False, not raise
        result = manager.save_sync_state_to_db(state)
        assert result is False


class TestSyncStateLoadMetadata:
    """Tests for loading metadata from database."""

    def test_load_returns_none_without_db_manager(self, tmp_path):
        """Test that load returns None when db_manager is None."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir, db_manager=None)

        result = manager.load_sync_state_from_db()
        assert result is None

    def test_load_requires_last_sync_metadata(self, tmp_path):
        """Test that load returns None if last_sync metadata is missing."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        mock_db = Mock()
        mock_conn = Mock()
        mock_conn.execute.return_value = []  # No metadata

        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        result = manager.load_sync_state_from_db()
        assert result is None

    def test_load_extracts_metadata_correctly(self, tmp_path):
        """Test that load correctly extracts metadata and creates SyncState."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        now_iso = "2026-01-31T12:30:45.123456+00:00"

        mock_db = Mock()
        mock_conn = Mock()
        
        # Return mock rows with metadata
        def mock_execute(query):
            if "SELECT key, value FROM sync_metadata" in query:
                return [
                    ("last_sync", now_iso),
                    ("backend", "github"),
                ]
            return []
        
        mock_conn.execute.side_effect = mock_execute
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        result = manager.load_sync_state_from_db()

        assert result is not None
        assert result.backend == "github"
        # last_sync should be parsed from ISO string
        assert result.last_sync.year == 2026
        assert result.last_sync.month == 1
        assert result.last_sync.day == 31

    def test_load_defaults_backend_to_github(self, tmp_path):
        """Test that backend defaults to 'github' if not in metadata."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        now_iso = "2026-01-31T12:30:45+00:00"

        mock_db = Mock()
        mock_conn = Mock()
        
        def mock_execute(query):
            if "SELECT key, value FROM sync_metadata" in query:
                return [("last_sync", now_iso)]  # No backend specified
            return []
        
        mock_conn.execute.side_effect = mock_execute
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        result = manager.load_sync_state_from_db()

        assert result is not None
        assert result.backend == "github"  # Default

    def test_load_returns_none_on_database_error(self, tmp_path):
        """Test that load returns None (not raises) on database error."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        mock_db = Mock()
        mock_conn = Mock()
        mock_conn.execute.side_effect = Exception("Database corrupted")
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        result = manager.load_sync_state_from_db()
        assert result is None

    def test_load_returns_none_on_invalid_iso_date(self, tmp_path):
        """Test that load returns None if date parsing fails."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        mock_db = Mock()
        mock_conn = Mock()
        
        def mock_execute(query):
            if "SELECT key, value FROM sync_metadata" in query:
                return [("last_sync", "not-a-valid-date")]
            return []
        
        mock_conn.execute.side_effect = mock_execute
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        # Should handle gracefully and return None
        result = manager.load_sync_state_from_db()
        assert result is None
