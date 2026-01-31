"""Tests for SyncStateManager.

Tests persistence and loading of sync state for three-way merge operations.
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from roadmap.core.models.sync_state import IssueBaseState, SyncState
from roadmap.core.services.sync.sync_state_manager import SyncStateManager


class TestSyncStateManagerInit:
    """Test SyncStateManager initialization."""

    def test_initialization_with_roadmap_dir(self, tmp_path):
        """Test manager initializes with roadmap directory."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir)

        assert manager.roadmap_dir == roadmap_dir
        assert manager.state_file == roadmap_dir / "sync_state.json"
        assert manager.db_manager is None

    def test_initialization_with_db_manager(self, tmp_path):
        """Test manager initializes with optional database manager."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        mock_db = Mock()

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        assert manager.db_manager is mock_db


class TestLoadSyncState:
    """Test load_sync_state deprecated method."""

    def test_load_sync_state_returns_none(self, tmp_path):
        """Test load_sync_state returns None (deprecated method)."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir)

        result = manager.load_sync_state()

        assert result is None


class TestSaveSyncState:
    """Test save_sync_state deprecated method."""

    def test_save_sync_state_returns_true(self, tmp_path):
        """Test save_sync_state returns True (deprecated method)."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir)
        state = SyncState(
            last_sync=datetime.now(UTC),
            backend="github",
        )

        result = manager.save_sync_state(state)

        assert result is True


class TestSaveSyncStateToDb:
    """Test save_sync_state_to_db method."""

    def test_save_to_db_without_manager_returns_false(self, tmp_path):
        """Test save_sync_state_to_db returns False when no db_manager."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir)  # No db_manager
        state = SyncState(
            last_sync=datetime.now(UTC),
            backend="github",
        )

        result = manager.save_sync_state_to_db(state)

        assert result is False

    @patch("roadmap.core.services.sync.sync_state_manager.datetime")
    def test_save_to_db_with_manager_success(self, mock_datetime, tmp_path):
        """Test save_sync_state_to_db saves state successfully."""
        now = datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = now
        mock_datetime.fromisoformat = datetime.fromisoformat
        mock_datetime.UTC = UTC

        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        mock_db = Mock()
        mock_conn = Mock()
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)
        state = SyncState(
            last_sync=now,
            backend="github",
        )

        result = manager.save_sync_state_to_db(state)

        assert result is True
        mock_db._get_connection.assert_called_once()
        mock_conn.execute.assert_called()
        mock_conn.commit.assert_called_once()

    @pytest.mark.parametrize(
        "issue_id,status,assignee,milestone",
        [
            ("ISSUE-1", "open", "user1", "v1.0"),
            ("ISSUE-2", "closed", None, None),
            ("ISSUE-3", "in_progress", "user2", "v2.0"),
        ],
    )
    @patch("roadmap.core.services.sync.sync_state_manager.datetime")
    def test_save_to_db_with_multiple_issues(
        self, mock_datetime, issue_id, status, assignee, milestone, tmp_path
    ):
        """Test save_sync_state_to_db saves multiple issues."""
        now = datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = now
        mock_datetime.fromisoformat = datetime.fromisoformat
        mock_datetime.UTC = UTC

        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        mock_db = Mock()
        mock_conn = Mock()
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        base_state = IssueBaseState(
            id=issue_id,
            status=status,
            title="Test Issue",
            assignee=assignee,
            milestone=milestone,
            headline="Test",
            content="Content",
            labels=["bug", "feature"],
        )

        state = SyncState(
            last_sync=now,
            backend="github",
            issues={issue_id: base_state},
        )

        result = manager.save_sync_state_to_db(state)

        assert result is True
        # Verify execute was called for metadata and issue state
        assert mock_conn.execute.call_count >= 2

    def test_save_to_db_handles_exception(self, tmp_path):
        """Test save_sync_state_to_db handles database errors gracefully."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        mock_db = Mock()
        mock_conn = Mock()
        mock_conn.execute.side_effect = Exception("DB error")
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)
        state = SyncState(
            last_sync=datetime.now(UTC),
            backend="github",
        )

        result = manager.save_sync_state_to_db(state)

        assert result is False

    @patch("roadmap.core.services.sync.sync_state_manager.datetime")
    def test_save_to_db_with_empty_issues(self, mock_datetime, tmp_path):
        """Test save_sync_state_to_db with empty issues dict."""
        now = datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = now
        mock_datetime.fromisoformat = datetime.fromisoformat
        mock_datetime.UTC = UTC

        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        mock_db = Mock()
        mock_conn = Mock()
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)
        state = SyncState(
            last_sync=now,
            backend="github",
            issues={},  # Empty
        )

        result = manager.save_sync_state_to_db(state)

        assert result is True


class TestLoadSyncStateFromDb:
    """Test load_sync_state_from_db method."""

    def test_load_from_db_without_manager_returns_none(self, tmp_path):
        """Test load_sync_state_from_db returns None when no db_manager."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir)  # No db_manager

        result = manager.load_sync_state_from_db()

        assert result is None

    @patch("roadmap.core.services.sync.sync_state_manager.datetime")
    def test_load_from_db_with_valid_metadata(self, mock_datetime, tmp_path):
        """Test load_sync_state_from_db loads valid state."""
        now = datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC)
        mock_datetime.fromisoformat.return_value = now

        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        mock_db = Mock()
        mock_conn = Mock()

        # Mock metadata query results
        mock_conn.execute.return_value = [
            ("last_sync", now.isoformat()),
            ("backend", "github"),
        ]

        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        result = manager.load_sync_state_from_db()

        assert result is not None
        assert result.backend == "github"
        assert (
            len(result.issues) == 0
        )  # Issues loading disabled in current implementation

    def test_load_from_db_with_no_last_sync_returns_none(self, tmp_path):
        """Test load_sync_state_from_db returns None when no last_sync metadata."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        mock_db = Mock()
        mock_conn = Mock()

        # Mock metadata query with no last_sync
        mock_conn.execute.return_value = []

        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        result = manager.load_sync_state_from_db()

        assert result is None

    def test_load_from_db_handles_exception(self, tmp_path):
        """Test load_sync_state_from_db handles database errors gracefully."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        mock_db = Mock()
        mock_conn = Mock()
        mock_conn.execute.side_effect = Exception("DB error")
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        result = manager.load_sync_state_from_db()

        assert result is None

    @patch("roadmap.core.services.sync.sync_state_manager.datetime")
    def test_load_from_db_default_backend(self, mock_datetime, tmp_path):
        """Test load_sync_state_from_db defaults to github backend."""
        now = datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC)
        mock_datetime.fromisoformat.return_value = now

        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        mock_db = Mock()
        mock_conn = Mock()

        # Mock metadata query with only last_sync (no backend)
        mock_conn.execute.return_value = [
            ("last_sync", now.isoformat()),
        ]

        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        result = manager.load_sync_state_from_db()

        assert result is not None
        assert result.backend == "github"  # Default


class TestSyncStateIntegration:
    """Integration tests for sync state management."""

    def test_roundtrip_save_and_load(self, tmp_path):
        """Test saving and loading state maintains data integrity."""
        now = datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC)

        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        mock_db = Mock()
        mock_conn = Mock()

        # Setup mock for saving
        call_count = [0]

        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if "SELECT key, value FROM sync_metadata" in str(args[0]):
                return [
                    ("last_sync", now.isoformat()),
                    ("backend", "github"),
                ]
            return []

        mock_conn.execute.side_effect = execute_side_effect
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        # Save state
        state_to_save = SyncState(
            last_sync=now,
            backend="github",
        )
        save_result = manager.save_sync_state_to_db(state_to_save)
        assert save_result is True

        # Load state
        with patch(
            "roadmap.core.services.sync.sync_state_manager.datetime"
        ) as mock_datetime:
            mock_datetime.fromisoformat.return_value = now

            loaded_state = manager.load_sync_state_from_db()

        assert loaded_state is not None
        assert loaded_state.backend == "github"
        assert loaded_state.last_sync == now
