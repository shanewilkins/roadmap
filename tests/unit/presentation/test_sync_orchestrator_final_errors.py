"""Error path tests for SyncOrchestrator module.

Tests cover incremental sync, full rebuild, decision logic,
error handling, and file synchronization.
"""

from pathlib import Path
from unittest import mock

from roadmap.adapters.persistence.sync_orchestrator import SyncOrchestrator
from tests.fixtures import build_mock_path


class TestSyncOrchestratorInitialization:
    """Test SyncOrchestrator initialization."""

    import pytest

    @pytest.mark.parametrize(
        "get_conn,trans,expected_callable",
        [
            (mock.MagicMock(), mock.MagicMock(), False),
            (lambda: mock.MagicMock(), lambda: None, True),
        ],
    )
    def test_initialization_param(self, get_conn, trans, expected_callable):
        orchestrator = SyncOrchestrator(get_conn, trans)
        if expected_callable:
            assert callable(orchestrator._get_connection)
            assert callable(orchestrator._transaction)
        else:
            assert orchestrator._get_connection == get_conn
            assert orchestrator._transaction == trans


class TestHasFileChanged:
    """Test _has_file_changed method."""

    import pytest

    @pytest.mark.parametrize(
        "desc,setup_fn,expected",
        [
            ("file_not_exists", lambda: (False, None, None, None), True),
            ("file_never_synced", lambda: (True, None, None, None), True),
            ("file_hash_matches", lambda: (True, "abc123", "abc123", None), False),
            ("file_hash_differs", lambda: (True, "old_hash", "new_hash", None), True),
            (
                "file_check_error",
                lambda: (True, None, None, Exception("DB error")),
                True,
            ),
        ],
    )
    def test_has_file_changed_param(self, desc, setup_fn, expected):
        file_exists, stored_hash, calc_hash, error = setup_fn()
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()
        if error:
            mock_get_conn.side_effect = error
        else:
            mock_conn = mock.MagicMock()
            if stored_hash is not None:
                mock_conn.execute.return_value.fetchone.return_value = (stored_hash,)
            else:
                mock_conn.execute.return_value.fetchone.return_value = None
            mock_get_conn.return_value = mock_conn
        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)
        mock_file = build_mock_path()
        mock_file.exists.return_value = file_exists
        if calc_hash is not None or stored_hash is not None:
            with mock.patch.object(
                orchestrator._parser, "calculate_file_hash"
            ) as mock_hash:
                mock_hash.return_value = calc_hash or stored_hash
                result = orchestrator._has_file_changed(mock_file)
        else:
            result = orchestrator._has_file_changed(mock_file)
        assert result is expected


class TestSyncFileByType:
    """Test _sync_file_by_type method."""

    def test_sync_issue_file(self):
        """Test syncing issue file."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_file = build_mock_path()
        mock_file.__str__ = mock.MagicMock(return_value="issues/test.md")

        stats = {"files_synced": 0, "files_failed": 0}

        with mock.patch.object(
            orchestrator._issue_sync, "sync_issue_file"
        ) as mock_sync:
            mock_sync.return_value = True
            result = orchestrator._sync_file_by_type(mock_file, stats)

            assert result is True
            assert stats["files_synced"] == 1

    def test_sync_milestone_file(self):
        """Test syncing milestone file."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_file = build_mock_path()
        mock_file.__str__ = mock.MagicMock(return_value="milestones/v1.0.md")

        stats = {"files_synced": 0, "files_failed": 0}

        with mock.patch.object(
            orchestrator._milestone_sync, "sync_milestone_file"
        ) as mock_sync:
            mock_sync.return_value = True
            result = orchestrator._sync_file_by_type(mock_file, stats)

            assert result is True
            assert stats["files_synced"] == 1

    def test_sync_project_file(self):
        """Test syncing project file."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_file = build_mock_path()
        mock_file.__str__ = mock.MagicMock(return_value="projects/backend.md")

        stats = {"files_synced": 0, "files_failed": 0}

        with mock.patch.object(
            orchestrator._project_sync, "sync_project_file"
        ) as mock_sync:
            mock_sync.return_value = True
            result = orchestrator._sync_file_by_type(mock_file, stats)

            assert result is True
            assert stats["files_synced"] == 1

    def test_sync_file_type_unknown(self):
        """Test with unknown file type."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_file = build_mock_path()
        mock_file.__str__ = mock.MagicMock(return_value="other/file.md")

        stats = {"files_synced": 0, "files_failed": 0}

        result = orchestrator._sync_file_by_type(mock_file, stats)

        assert result is False

    def test_sync_file_failure(self):
        """Test handling of sync failure."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_file = build_mock_path()
        mock_file.__str__ = mock.MagicMock(return_value="issues/test.md")

        stats = {"files_synced": 0, "files_failed": 0}

        with mock.patch.object(
            orchestrator._issue_sync, "sync_issue_file"
        ) as mock_sync:
            mock_sync.return_value = False
            result = orchestrator._sync_file_by_type(mock_file, stats)

            assert result is False
            assert stats["files_failed"] == 1


class TestSyncDirectoryIncremental:
    """Test sync_directory_incremental method."""

    def test_sync_directory_not_exists(self):
        """Test when directory doesn't exist."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_dir = build_mock_path(is_dir=True)
        mock_dir.exists.return_value = False

        result = orchestrator.sync_directory_incremental(mock_dir)

        assert result["files_checked"] == 0
        assert result["files_synced"] == 0

    def test_sync_directory_empty(self):
        """Test syncing empty directory."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_dir = build_mock_path(is_dir=True)
        mock_dir.exists.return_value = True
        mock_dir.glob.return_value = []

        result = orchestrator.sync_directory_incremental(mock_dir)

        assert result["files_checked"] == 0
        assert result["files_synced"] == 0
        assert "sync_time" in result

    def test_sync_directory_with_files(self):
        """Test syncing directory with files."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_file = build_mock_path()
        mock_file.__str__ = mock.MagicMock(return_value="issues/test.md")

        mock_dir = build_mock_path(is_dir=True)
        mock_dir.exists.return_value = True
        mock_dir.glob.side_effect = [[mock_file], [], []]

        with mock.patch.object(orchestrator, "_has_file_changed") as mock_check:
            mock_check.return_value = False

            result = orchestrator.sync_directory_incremental(mock_dir)

            assert result["files_checked"] == 1

    def test_sync_directory_error(self):
        """Test error handling in directory sync."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_dir = build_mock_path(is_dir=True)
        mock_dir.exists.side_effect = Exception("IO error")

        result = orchestrator.sync_directory_incremental(mock_dir)

        assert result["files_failed"] >= 0


class TestFullRebuildFromGit:
    """Test full_rebuild_from_git method."""

    def test_rebuild_directory_not_exists(self):
        """Test rebuild when directory doesn't exist."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_dir = build_mock_path(is_dir=True)
        mock_dir.exists.return_value = False

        result = orchestrator.full_rebuild_from_git(mock_dir)

        assert result["files_processed"] == 0
        assert "rebuild_time" in result

    def test_rebuild_empty_directory(self):
        """Test rebuild with empty directory."""
        mock_get_conn = mock.MagicMock()
        mock_conn = mock.MagicMock()
        mock_get_conn.return_value = mock_conn

        mock_transaction = mock.MagicMock()
        mock_transaction.return_value.__enter__ = mock.MagicMock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = mock.MagicMock(return_value=False)

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_dir = build_mock_path(is_dir=True)
        mock_dir.exists.return_value = True
        mock_dir.glob.return_value = []

        result = orchestrator.full_rebuild_from_git(mock_dir)

        assert result["files_processed"] == 0


class TestShouldDoFullRebuild:
    """Test should_do_full_rebuild method."""

    def test_no_previous_sync(self):
        """Test when there's no previous sync checkpoint."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_dir = build_mock_path(is_dir=True)
        mock_dir.exists.return_value = True
        mock_dir.glob.side_effect = [[], [], []]  # No files

        with mock.patch.object(
            orchestrator._state_tracker, "get_last_incremental_sync"
        ) as mock_check:
            mock_check.return_value = None

            result = orchestrator.should_do_full_rebuild(mock_dir)

            assert result is True

    def test_threshold_not_exceeded(self):
        """Test when file change threshold is not exceeded."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        # Create 10 mock files for testing
        mock_files = [mock.MagicMock(spec=Path) for _ in range(10)]

        mock_dir = build_mock_path(is_dir=True)
        mock_dir.exists.return_value = True

        # Mock glob to return files matching patterns
        # The function calls glob 6 times (3 patterns x 2 loops)
        def glob_side_effect(pattern):
            if "issues" in pattern:
                return mock_files  # 10 files
            else:
                return []  # No milestones or projects

        mock_dir.glob = mock.MagicMock(side_effect=glob_side_effect)

        with mock.patch.object(
            orchestrator._state_tracker, "get_last_incremental_sync"
        ) as mock_sync:
            mock_sync.return_value = "2024-01-01"  # Has previous sync

            with mock.patch.object(orchestrator, "_has_file_changed") as mock_changed:
                # Only 1 out of 10 files changed (10% < 50% threshold)
                mock_changed.side_effect = [True] + [False] * 9

                result = orchestrator.should_do_full_rebuild(mock_dir, threshold=50)

                # 1 changed out of 10 = 10% < 50%, so should return False
                assert result is False

    def test_rebuild_decision_error(self):
        """Test error handling in rebuild decision."""
        mock_get_conn = mock.MagicMock()
        mock_transaction = mock.MagicMock()

        orchestrator = SyncOrchestrator(mock_get_conn, mock_transaction)

        mock_dir = build_mock_path(is_dir=True)
        mock_dir.exists.return_value = True
        mock_dir.glob.side_effect = Exception("IO error")

        result = orchestrator.should_do_full_rebuild(mock_dir)

        # Should default to True on error
        assert result is True
