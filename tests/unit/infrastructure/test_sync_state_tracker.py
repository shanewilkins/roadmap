"""
Tests for sync state tracking.
"""

import tempfile
from pathlib import Path

import pytest

from roadmap.infrastructure.persistence.database_manager import DatabaseManager
from roadmap.infrastructure.persistence.sync_state_tracker import SyncStateTracker


class TestSyncStateTracker:
    """Test SyncStateTracker for managing sync metadata."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        try:
            db_path.unlink()
            wal_path = Path(str(db_path) + "-wal")
            shm_path = Path(str(db_path) + "-shm")
            if wal_path.exists():
                wal_path.unlink()
            if shm_path.exists():
                shm_path.unlink()
        except Exception:
            pass

    @pytest.fixture
    def sync_tracker(self, temp_db):
        """Create a SyncStateTracker with temp database."""
        db_manager = DatabaseManager(db_path=temp_db)
        return SyncStateTracker(db_manager._get_connection)

    def test_set_and_get_sync_state(self, sync_tracker):
        """set_sync_state and get_sync_state should store and retrieve values."""
        sync_tracker.set_sync_state("test_key", "test_value")
        assert sync_tracker.get_sync_state("test_key") == "test_value"

    def test_get_nonexistent_sync_state_returns_none(self, sync_tracker):
        """get_sync_state should return None for non-existent keys."""
        assert sync_tracker.get_sync_state("nonexistent") is None

    def test_update_sync_state_overwrites_value(self, sync_tracker):
        """set_sync_state should overwrite existing values."""
        sync_tracker.set_sync_state("test_key", "value1")
        sync_tracker.set_sync_state("test_key", "value2")
        assert sync_tracker.get_sync_state("test_key") == "value2"

    def test_has_git_conflicts_returns_false_by_default(self, sync_tracker):
        """has_git_conflicts should return False when no conflicts detected."""
        assert sync_tracker.has_git_conflicts() is False

    def test_has_git_conflicts_returns_true_when_marked(self, sync_tracker):
        """has_git_conflicts should return True after marking conflicts."""
        sync_tracker.mark_conflicts_detected(["file1.md", "file2.md"])
        assert sync_tracker.has_git_conflicts() is True

    def test_get_conflict_files_empty_list_by_default(self, sync_tracker):
        """get_conflict_files should return empty list by default."""
        assert sync_tracker.get_conflict_files() == []

    def test_get_conflict_files_returns_marked_files(self, sync_tracker):
        """get_conflict_files should return files marked with conflicts."""
        files = ["file1.md", "file2.md", "file3.md"]
        sync_tracker.mark_conflicts_detected(files)
        assert sync_tracker.get_conflict_files() == files

    def test_mark_conflicts_detected_sets_flag(self, sync_tracker):
        """mark_conflicts_detected should set conflict flag and file list."""
        files = ["conflict1.md", "conflict2.md"]
        sync_tracker.mark_conflicts_detected(files)

        assert sync_tracker.has_git_conflicts() is True
        assert sync_tracker.get_conflict_files() == files

    def test_clear_conflicts_removes_flag(self, sync_tracker):
        """clear_conflicts should remove conflict markers."""
        sync_tracker.mark_conflicts_detected(["file1.md"])
        assert sync_tracker.has_git_conflicts() is True

        sync_tracker.clear_conflicts()
        assert sync_tracker.has_git_conflicts() is False
        assert sync_tracker.get_conflict_files() == []

    def test_update_last_incremental_sync(self, sync_tracker):
        """update_last_incremental_sync should store timestamp."""
        sync_time = "2024-01-15T10:30:00Z"
        sync_tracker.update_last_incremental_sync(sync_time)
        assert sync_tracker.get_last_incremental_sync() == sync_time

    def test_get_last_incremental_sync_returns_none_initially(self, sync_tracker):
        """get_last_incremental_sync should return None when never synced."""
        assert sync_tracker.get_last_incremental_sync() is None

    def test_update_last_full_rebuild(self, sync_tracker):
        """update_last_full_rebuild should store timestamp."""
        rebuild_time = "2024-01-15T10:30:00Z"
        sync_tracker.update_last_full_rebuild(rebuild_time)
        assert sync_tracker.get_last_full_rebuild() == rebuild_time

    def test_get_last_full_rebuild_returns_none_initially(self, sync_tracker):
        """get_last_full_rebuild should return None when never rebuilt."""
        assert sync_tracker.get_last_full_rebuild() is None

    def test_multiple_sync_state_keys_independent(self, sync_tracker):
        """Multiple sync state keys should be independent."""
        sync_tracker.set_sync_state("key1", "value1")
        sync_tracker.set_sync_state("key2", "value2")
        sync_tracker.set_sync_state("key3", "value3")

        assert sync_tracker.get_sync_state("key1") == "value1"
        assert sync_tracker.get_sync_state("key2") == "value2"
        assert sync_tracker.get_sync_state("key3") == "value3"

    def test_conflict_files_persists_across_calls(self, sync_tracker):
        """Conflict files should persist in database."""
        files1 = ["file1.md", "file2.md"]
        sync_tracker.mark_conflicts_detected(files1)

        # Test that the same conflict data is retrievable
        assert sync_tracker.get_conflict_files() == files1

    def test_sync_timestamps_persist(self, sync_tracker):
        """Sync timestamps should persist in database."""
        sync_time = "2024-01-15T10:30:00Z"
        sync_tracker.update_last_incremental_sync(sync_time)

        # Verify persistence
        assert sync_tracker.get_last_incremental_sync() == sync_time

    def test_error_handling_on_invalid_json(self, sync_tracker):
        """get_conflict_files should handle invalid JSON gracefully."""
        # Manually set invalid JSON
        sync_tracker.set_sync_state("conflict_files", "invalid json {")
        # Should return empty list on error
        result = sync_tracker.get_conflict_files()
        assert isinstance(result, list)

    def test_error_handling_on_database_issues(self, sync_tracker):
        """has_git_conflicts should handle database errors gracefully."""
        # Close the database connection
        conn = sync_tracker._get_connection()
        try:
            conn.close()
        except Exception:
            pass

        # Should return False on error instead of crashing
        result = sync_tracker.has_git_conflicts()
        assert isinstance(result, bool)
