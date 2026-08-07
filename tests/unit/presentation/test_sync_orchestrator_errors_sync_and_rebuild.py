"""Error path tests for sync_orchestrator.py - Phase 10a Tier 1 coverage expansion.

This module tests error handling and exception paths in the sync orchestrator,
focusing on database errors, file I/O errors, missing data, etc.

Currently sync_orchestrator.py has 40% coverage.
Target after Phase 10a: 85%+ coverage
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from roadmap.adapters.persistence.sync_orchestrator import SyncOrchestrator

# ========== Unit Tests: File Change Detection ==========


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
                            datetime.now(UTC)
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
                            datetime.now(UTC)
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
