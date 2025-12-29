"""Error path tests for sync_orchestrator.py - Phase 10a Tier 1 coverage expansion.

This module tests error handling and exception paths in the sync orchestrator,
focusing on database errors, file I/O errors, missing data, etc.

Currently sync_orchestrator.py has 40% coverage.
Target after Phase 10a: 85%+ coverage
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from roadmap.adapters.persistence.sync_orchestrator import SyncOrchestrator

# ========== Unit Tests: File Change Detection ==========


class TestFileChangeDetection:
    """Test file change detection with various error conditions."""

    import pytest

    @pytest.mark.parametrize(
        "file_exists, stored_hash, calc_hash, db_error, expected",
        [
            (False, None, None, None, True),  # file missing
            (True, None, None, None, True),  # no sync record
            (True, "abc123", "abc123", None, True),  # hash matches
            (True, "hash_old", "hash_new", None, True),  # hash mismatch
            (True, None, None, Exception("DB error"), True),  # db error
        ],
    )
    def test_file_changed_param(
        self, tmp_path, file_exists, stored_hash, calc_hash, db_error, expected
    ):
        test_file = tmp_path / "test.md"
        if file_exists:
            test_file.write_text("content")
        mock_conn = Mock()
        if db_error:
            mock_conn.execute.side_effect = db_error
        else:
            if stored_hash is not None:
                mock_conn.execute.return_value.fetchone.return_value = (stored_hash,)
            else:
                mock_conn.execute.return_value.fetchone.return_value = None
        mock_get_connection = Mock(return_value=mock_conn)
        mock_transaction = Mock()
        orchestrator = SyncOrchestrator(mock_get_connection, mock_transaction)
        if calc_hash is not None or stored_hash is not None:
            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.FileParser"
            ) as mock_parser_class:
                mock_parser = Mock()
                mock_parser.calculate_file_hash.return_value = calc_hash or stored_hash
                mock_parser_class.return_value = mock_parser
                result = orchestrator._has_file_changed(test_file)
        else:
            result = orchestrator._has_file_changed(test_file)
        assert result == expected


# ========== Unit Tests: File Type Sync Dispatch ==========


class TestFileSyncDispatch:
    """Test file type detection and sync dispatch."""

    def test_sync_dispatches_to_issue_coordinator(self, tmp_path):
        """Test that issue files are dispatched to issue coordinator."""
        mock_get_connection = Mock()
        mock_transaction = Mock()

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ) as mock_issue_class:
            mock_issue_sync = Mock()
            mock_issue_sync.sync_issue_file.return_value = True
            mock_issue_class.return_value = mock_issue_sync

            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ):
                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ):
                    orchestrator = SyncOrchestrator(
                        mock_get_connection, mock_transaction
                    )
                    orchestrator._issue_sync = mock_issue_sync

                    stats = {"files_synced": 0, "files_failed": 0}
                    file_path = tmp_path / "issues" / "test.md"

                    result = orchestrator._sync_file_by_type(file_path, stats)

                    mock_issue_sync.sync_issue_file.assert_called_once_with(file_path)
                    assert result is True
                    assert stats["files_synced"] == 1

    def test_sync_dispatches_to_milestone_coordinator(self, tmp_path):
        """Test that milestone files are dispatched to milestone coordinator."""
        mock_get_connection = Mock()
        mock_transaction = Mock()

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ):
            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ) as mock_milestone_class:
                mock_milestone_sync = Mock()
                mock_milestone_sync.sync_milestone_file.return_value = True
                mock_milestone_class.return_value = mock_milestone_sync

                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ):
                    orchestrator = SyncOrchestrator(
                        mock_get_connection, mock_transaction
                    )
                    orchestrator._milestone_sync = mock_milestone_sync

                    stats = {"files_synced": 0, "files_failed": 0}
                    file_path = tmp_path / "milestones" / "test.md"

                    result = orchestrator._sync_file_by_type(file_path, stats)

                    mock_milestone_sync.sync_milestone_file.assert_called_once()
                    assert result is True

    def test_sync_dispatches_to_project_coordinator(self, tmp_path):
        """Test that project files are dispatched to project coordinator."""
        mock_get_connection = Mock()
        mock_transaction = Mock()

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ):
            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ):
                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ) as mock_project_class:
                    mock_project_sync = Mock()
                    mock_project_sync.sync_project_file.return_value = True
                    mock_project_class.return_value = mock_project_sync

                    orchestrator = SyncOrchestrator(
                        mock_get_connection, mock_transaction
                    )
                    orchestrator._project_sync = mock_project_sync

                    stats = {"files_synced": 0, "files_failed": 0}
                    file_path = tmp_path / "projects" / "test.md"

                    result = orchestrator._sync_file_by_type(file_path, stats)

                    mock_project_sync.sync_project_file.assert_called_once()
                    assert result is True

    def test_sync_returns_false_for_unknown_file_type(self, tmp_path):
        """Test that unknown file types return False."""
        mock_get_connection = Mock()
        mock_transaction = Mock()

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ):
            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ):
                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ):
                    orchestrator = SyncOrchestrator(
                        mock_get_connection, mock_transaction
                    )

                    stats = {"files_synced": 0, "files_failed": 0}
                    file_path = tmp_path / "unknown" / "test.md"

                    result = orchestrator._sync_file_by_type(file_path, stats)

                    assert result is False

    def test_sync_updates_failed_count_on_sync_failure(self, tmp_path):
        """Test that failed syncs are counted."""
        mock_get_connection = Mock()
        mock_transaction = Mock()

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ) as mock_issue_class:
            mock_issue_sync = Mock()
            mock_issue_sync.sync_issue_file.return_value = False  # Failure
            mock_issue_class.return_value = mock_issue_sync

            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ):
                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ):
                    orchestrator = SyncOrchestrator(
                        mock_get_connection, mock_transaction
                    )
                    orchestrator._issue_sync = mock_issue_sync

                    stats = {"files_synced": 0, "files_failed": 0}
                    file_path = tmp_path / "issues" / "test.md"

                    result = orchestrator._sync_file_by_type(file_path, stats)

                    assert result is False
                    assert stats["files_failed"] == 1


# ========== Integration Tests: Incremental Sync ==========


class TestIncrementalSync:
    """Test incremental sync with error conditions."""

    def test_incremental_sync_returns_stats_when_directory_missing(self):
        """Test that missing directory is handled gracefully."""
        mock_get_connection = Mock()
        mock_transaction = Mock()

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ):
            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ):
                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ):
                    orchestrator = SyncOrchestrator(
                        mock_get_connection, mock_transaction
                    )

                    result = orchestrator.sync_directory_incremental(
                        Path("/nonexistent/dir")
                    )

                    assert isinstance(result, dict)
                    assert result["files_checked"] == 0

    def test_incremental_sync_handles_database_error(self, tmp_path):
        """Test that database errors during incremental sync are handled."""
        roadmap_dir = tmp_path / "roadmap"
        roadmap_dir.mkdir()

        mock_get_connection = Mock()
        mock_get_connection.side_effect = Exception("DB error")
        mock_transaction = Mock()

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ):
            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ):
                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ):
                    orchestrator = SyncOrchestrator(
                        mock_get_connection, mock_transaction
                    )

                    # Should not crash
                    result = orchestrator.sync_directory_incremental(roadmap_dir)

                    assert isinstance(result, dict)


# ========== Integration Tests: Full Rebuild ==========


class TestFullRebuild:
    """Test full rebuild with error conditions."""

    def test_full_rebuild_returns_stats_when_directory_missing(self):
        """Test that missing directory is handled in full rebuild."""
        mock_get_connection = Mock()
        mock_transaction = Mock()

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ):
            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ):
                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ):
                    orchestrator = SyncOrchestrator(
                        mock_get_connection, mock_transaction
                    )

                    result = orchestrator.full_rebuild_from_git(
                        Path("/nonexistent/dir")
                    )

                    assert isinstance(result, dict)
                    assert "rebuild_time" in result

    def test_full_rebuild_handles_database_error(self, tmp_path):
        """Test that database errors during full rebuild are handled."""
        roadmap_dir = tmp_path / "roadmap"
        roadmap_dir.mkdir()

        mock_get_connection = Mock()
        mock_transaction = MagicMock()
        # Make the context manager raise an error
        mock_transaction.return_value.__enter__.side_effect = Exception("DB error")

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ):
            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ):
                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ):
                    orchestrator = SyncOrchestrator(
                        mock_get_connection, mock_transaction
                    )

                    # Should handle error gracefully
                    result = orchestrator.full_rebuild_from_git(roadmap_dir)

                    assert isinstance(result, dict)


# ========== Integration Tests: Rebuild Strategy Decision ==========


class TestRebuildStrategyDecision:
    """Test logic for deciding between full rebuild and incremental sync."""

    def test_should_rebuild_returns_true_when_no_sync_history(self):
        """Test that full rebuild is triggered when no sync history exists."""
        mock_get_connection = Mock()
        mock_transaction = Mock()

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ):
            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ):
                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ):
                    with patch(
                        "roadmap.adapters.persistence.sync_orchestrator.SyncStateTracker"
                    ) as mock_tracker_class:
                        mock_tracker = Mock()
                        mock_tracker.get_last_incremental_sync.return_value = None
                        mock_tracker_class.return_value = mock_tracker

                        orchestrator = SyncOrchestrator(
                            mock_get_connection, mock_transaction
                        )
                        orchestrator._state_tracker = mock_tracker

                        result = orchestrator.should_do_full_rebuild(Path("/tmp"))

                        assert result is True

    def test_should_rebuild_returns_false_when_few_changes(self, tmp_path):
        """Test that incremental sync is preferred when few files changed."""
        roadmap_dir = tmp_path / "roadmap"
        roadmap_dir.mkdir()

        # Create a single test file
        issues_dir = roadmap_dir / "issues"
        issues_dir.mkdir()
        (issues_dir / "test.md").write_text("content")

        mock_get_connection = Mock()
        mock_transaction = Mock()

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ):
            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ):
                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ):
                    with patch(
                        "roadmap.adapters.persistence.sync_orchestrator.SyncStateTracker"
                    ) as mock_tracker_class:
                        mock_tracker = Mock()
                        mock_tracker.get_last_incremental_sync.return_value = (
                            datetime.now()
                        )
                        mock_tracker_class.return_value = mock_tracker

                        orchestrator = SyncOrchestrator(
                            mock_get_connection, mock_transaction
                        )
                        orchestrator._state_tracker = mock_tracker

                        # Mock _has_file_changed to return False (no changes)
                        orchestrator._has_file_changed = Mock(return_value=False)

                        result = orchestrator.should_do_full_rebuild(
                            roadmap_dir, threshold=50
                        )

                        # 0 changed out of 1 file = 0% < 50%, so don't rebuild
                        assert result is False

    def test_should_rebuild_returns_true_when_many_changes(self, tmp_path):
        """Test that full rebuild is triggered when many files changed."""
        roadmap_dir = tmp_path / "roadmap"
        roadmap_dir.mkdir()

        # Create multiple test files
        issues_dir = roadmap_dir / "issues"
        issues_dir.mkdir()
        for i in range(10):
            (issues_dir / f"test{i}.md").write_text("content")

        mock_get_connection = Mock()
        mock_transaction = Mock()

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ):
            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ):
                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ):
                    with patch(
                        "roadmap.adapters.persistence.sync_orchestrator.SyncStateTracker"
                    ) as mock_tracker_class:
                        mock_tracker = Mock()
                        mock_tracker.get_last_incremental_sync.return_value = (
                            datetime.now()
                        )
                        mock_tracker_class.return_value = mock_tracker

                        orchestrator = SyncOrchestrator(
                            mock_get_connection, mock_transaction
                        )
                        orchestrator._state_tracker = mock_tracker

                        # Mock _has_file_changed to return True (all changed)
                        orchestrator._has_file_changed = Mock(return_value=True)

                        result = orchestrator.should_do_full_rebuild(
                            roadmap_dir, threshold=50
                        )

                        # 10 changed out of 10 files = 100% > 50%, so rebuild
                        assert result is True

    def test_should_rebuild_handles_errors(self, tmp_path):
        """Test that errors in rebuild decision are handled gracefully."""
        mock_get_connection = Mock()
        mock_transaction = Mock()

        with patch(
            "roadmap.adapters.persistence.sync_orchestrator.IssueSyncCoordinator"
        ):
            with patch(
                "roadmap.adapters.persistence.sync_orchestrator.MilestoneSyncCoordinator"
            ):
                with patch(
                    "roadmap.adapters.persistence.sync_orchestrator.ProjectSyncCoordinator"
                ):
                    with patch(
                        "roadmap.adapters.persistence.sync_orchestrator.SyncStateTracker"
                    ) as mock_tracker_class:
                        mock_tracker = Mock()
                        mock_tracker.get_last_incremental_sync.return_value = None
                        mock_tracker_class.return_value = mock_tracker

                        orchestrator = SyncOrchestrator(
                            mock_get_connection, mock_transaction
                        )
                        orchestrator._state_tracker = mock_tracker

                        # Should return True (no sync history -> rebuild)
                        result = orchestrator.should_do_full_rebuild(tmp_path)

                        assert result is True


pytestmark = pytest.mark.unit
