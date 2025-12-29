"""Error path tests for sync_orchestrator.py - Phase 10a Tier 1 coverage expansion.

This module tests error handling and exception paths in the sync orchestrator,
focusing on database errors, file I/O errors, missing data, etc.

Currently sync_orchestrator.py has 40% coverage.
Target after Phase 10a: 85%+ coverage
"""

from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.persistence.sync_orchestrator import SyncOrchestrator

# ========== Unit Tests: File Change Detection ==========


class TestFileChangeDetection:
    """Test file change detection with various error conditions."""

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
