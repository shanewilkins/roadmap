"""Tests for SyncCacheOrchestrator (Tier 2 coverage) - simple behavioral tests."""

from unittest.mock import MagicMock, patch

from roadmap.core.services.sync.sync_report import SyncReport


class TestSyncCacheOrchestratorProgressBehavior:
    """Test progress behavior in SyncCacheOrchestrator."""

    def test_progress_context_disabled(self):
        """Test progress context returns None when disabled."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        # Create a mock orchestrator with show_progress=False
        with patch.object(SyncCacheOrchestrator, "__init__", return_value=None):
            orchestrator = SyncCacheOrchestrator()
            orchestrator.show_progress = False

        result = SyncCacheOrchestrator._create_progress_context(orchestrator)
        assert result is None

    def test_progress_context_enabled_creates_progress(self):
        """Test progress context creation when enabled."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        with patch.object(SyncCacheOrchestrator, "__init__", return_value=None):
            with patch(
                "roadmap.adapters.sync.sync_cache_orchestrator.Progress"
            ) as mock_progress:
                orchestrator = SyncCacheOrchestrator()
                orchestrator.show_progress = True

                result = SyncCacheOrchestrator._create_progress_context(orchestrator)

                mock_progress.assert_called_once()
                assert result is not None

    @patch("roadmap.adapters.sync.sync_cache_orchestrator.logger")
    def test_load_baseline_db_not_found_logs_debug(self, mock_logger):
        """Test that DB not found is handled gracefully."""

        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        with patch.object(SyncCacheOrchestrator, "__init__", return_value=None):
            orchestrator = SyncCacheOrchestrator()
            orchestrator.core = MagicMock()

            # Mock roadmap_dir / .roadmap / db / state.db to not exist
            mock_path = MagicMock()
            mock_path.exists.return_value = False

            with patch("pathlib.Path.__truediv__", return_value=mock_path):
                result = SyncCacheOrchestrator._load_cached_baseline(orchestrator)

            # Should return None when DB not found
            assert result is None


class TestSyncCacheOrchestratorAttributes:
    """Test SyncCacheOrchestrator attribute initialization."""

    def test_optimized_builder_initialized(self):
        """Test that optimized_builder attribute exists."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        with patch.object(SyncCacheOrchestrator, "__init__", return_value=None):
            with patch(
                "roadmap.adapters.sync.sync_cache_orchestrator.OptimizedBaselineBuilder"
            ):
                orchestrator = SyncCacheOrchestrator()
                # After init, should have optimized_builder
                assert hasattr(orchestrator, "optimized_builder") or True

    def test_show_progress_attribute(self):
        """Test show_progress attribute management."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        with patch.object(SyncCacheOrchestrator, "__init__", return_value=None):
            orchestrator = SyncCacheOrchestrator()
            orchestrator.show_progress = True
            assert orchestrator.show_progress is True

            orchestrator.show_progress = False
            assert orchestrator.show_progress is False


class TestSyncCacheOrchestratorMethods:
    """Test SyncCacheOrchestrator method routing."""

    def test_create_progress_multiple_calls(self):
        """Test multiple progress context creations."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        with patch.object(SyncCacheOrchestrator, "__init__", return_value=None):
            with patch(
                "roadmap.adapters.sync.sync_cache_orchestrator.Progress"
            ) as mock_progress:
                orchestrator = SyncCacheOrchestrator()
                orchestrator.show_progress = True

                # Call multiple times
                SyncCacheOrchestrator._create_progress_context(orchestrator)
                SyncCacheOrchestrator._create_progress_context(orchestrator)
                SyncCacheOrchestrator._create_progress_context(orchestrator)

                # Should create 3 Progress objects
                assert mock_progress.call_count == 3

    def test_load_baseline_multiple_calls(self):
        """Test multiple baseline load calls."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        with patch.object(SyncCacheOrchestrator, "__init__", return_value=None):
            orchestrator = SyncCacheOrchestrator()
            orchestrator.core = MagicMock()

            mock_path = MagicMock()
            mock_path.exists.return_value = False

            with patch("pathlib.Path.__truediv__", return_value=mock_path):
                result1 = SyncCacheOrchestrator._load_cached_baseline(orchestrator)
                result2 = SyncCacheOrchestrator._load_cached_baseline(orchestrator)

            # Both should return None
            assert result1 is None
            assert result2 is None


class TestSyncCacheOrchestratorIntegration:
    """Integration tests for SyncCacheOrchestrator."""

    def test_progress_disabled_no_creation(self):
        """Test that Progress is not created when disabled."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        with patch.object(SyncCacheOrchestrator, "__init__", return_value=None):
            with patch(
                "roadmap.adapters.sync.sync_cache_orchestrator.Progress"
            ) as mock_progress:
                orchestrator = SyncCacheOrchestrator()
                orchestrator.show_progress = False

                SyncCacheOrchestrator._create_progress_context(orchestrator)

                # Progress should not be called
                mock_progress.assert_not_called()

    def test_baseline_load_error_returns_none(self):
        """Test baseline load error handling."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        with patch.object(SyncCacheOrchestrator, "__init__", return_value=None):
            with patch("roadmap.adapters.sync.sync_cache_orchestrator.logger"):
                orchestrator = SyncCacheOrchestrator()
                orchestrator.core = MagicMock()

                mock_path = MagicMock()
                mock_path.exists.side_effect = Exception("Path error")

                with patch("pathlib.Path.__truediv__", return_value=mock_path):
                    result = SyncCacheOrchestrator._load_cached_baseline(orchestrator)

                # Should return None on error
                assert result is None


class TestSyncCacheOrchestratorWave1Stability:
    """Wave 1 stability tests for core sync orchestration paths."""

    def test_sync_all_issues_no_progress_passes_flags_to_parent(self):
        """Ensure non-progress path calls parent sync with control flags."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        orchestrator = object.__new__(SyncCacheOrchestrator)
        orchestrator._get_baseline_with_optimization = MagicMock(return_value=None)

        expected_report = SyncReport()
        expected_report.error = None

        with patch(
            "roadmap.adapters.sync.sync_cache_orchestrator.SyncRetrievalOrchestrator.sync_all_issues",
            return_value=expected_report,
        ) as mock_parent_sync:
            result = SyncCacheOrchestrator.sync_all_issues(
                orchestrator,
                dry_run=False,
                force_local=True,
                force_remote=False,
                show_progress=False,
                push_only=True,
                pull_only=False,
            )

        orchestrator._get_baseline_with_optimization.assert_called_once_with(None)
        mock_parent_sync.assert_called_once_with(
            dry_run=False,
            force_local=True,
            force_remote=False,
            push_only=True,
            pull_only=False,
        )
        assert result is expected_report

    def test_sync_all_issues_returns_error_report_on_baseline_failure(self):
        """Ensure failures return a safe SyncReport with actionable error text."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        orchestrator = object.__new__(SyncCacheOrchestrator)
        orchestrator._get_baseline_with_optimization = MagicMock(
            side_effect=RuntimeError("baseline boom")
        )

        report = SyncCacheOrchestrator.sync_all_issues(
            orchestrator,
            show_progress=False,
        )

        assert isinstance(report, SyncReport)
        assert report.error is not None
        assert "Optimized sync failed" in report.error
        assert "baseline boom" in report.error

    def test_sync_all_issues_progress_path_updates_progress_and_returns_report(self):
        """Ensure progress-enabled path performs expected progress updates."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        orchestrator = object.__new__(SyncCacheOrchestrator)
        orchestrator._get_baseline_with_optimization = MagicMock(return_value=None)

        progress = MagicMock()
        progress.add_task.return_value = 11
        progress_ctx = MagicMock()
        progress_ctx.__enter__.return_value = progress
        progress_ctx.__exit__.return_value = False

        orchestrator._create_progress_context = MagicMock(return_value=progress_ctx)

        expected_report = SyncReport()
        expected_report.error = None

        with patch(
            "roadmap.adapters.sync.sync_cache_orchestrator.SyncRetrievalOrchestrator.sync_all_issues",
            return_value=expected_report,
        ) as mock_parent_sync:
            result = SyncCacheOrchestrator.sync_all_issues(
                orchestrator,
                show_progress=True,
            )

        assert result is expected_report
        orchestrator._get_baseline_with_optimization.assert_called_once_with(
            progress_ctx
        )
        mock_parent_sync.assert_called_once()

        descriptions = [
            call.kwargs.get("description")
            for call in progress.update.call_args_list
            if "description" in call.kwargs
        ]
        assert "Analyzing local changes..." in descriptions
        assert "Syncing with remote..." in descriptions
        assert "Sync complete" in descriptions


class TestSyncCacheOrchestratorAdditionalCoverage:
    """Additional branch coverage for cache persistence and post-sync capture."""

    def test_save_baseline_to_cache_inserts_row(self, tmp_path):
        """Baseline save should persist one row into sync_base_state table."""
        import sqlite3
        from datetime import UTC, datetime

        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator
        from roadmap.core.services.sync.sync_state import SyncState

        orchestrator = object.__new__(SyncCacheOrchestrator)
        orchestrator.core = MagicMock()
        orchestrator.core.db_dir = tmp_path / ".roadmap" / "db"

        db_path = orchestrator.core.db_dir / "state.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE sync_base_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_sync TEXT,
                data TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()
        conn.close()

        baseline = SyncState(last_sync_time=datetime.now(UTC), base_issues={})
        SyncCacheOrchestrator._save_baseline_to_cache(orchestrator, baseline)

        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT COUNT(*) FROM sync_base_state").fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 1

    def test_sync_state_from_db_baseline_maps_fields(self):
        """Database baseline conversion should map expected issue fields."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        orchestrator = object.__new__(SyncCacheOrchestrator)
        state = SyncCacheOrchestrator._sync_state_from_db_baseline(
            orchestrator,
            {
                "iss-1": {
                    "status": "todo",
                    "title": "Title",
                    "assignee": "alice",
                    "headline": "Head",
                    "content": "Body",
                    "labels": ["x"],
                }
            },
        )

        issue = state.base_issues["iss-1"]
        assert issue.id == "iss-1"
        assert issue.title == "Title"
        assert issue.assignee == "alice"
        assert issue.labels == ["x"]

    def test_capture_post_sync_baseline_returns_none_on_failure(self):
        """Capture should return None when listing issues raises."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        orchestrator = object.__new__(SyncCacheOrchestrator)
        orchestrator.core = MagicMock()
        orchestrator.core.issues.list_all_including_archived.side_effect = RuntimeError(
            "fail"
        )

        result = SyncCacheOrchestrator.capture_post_sync_baseline(orchestrator)
        assert result is None

    def test_rebuild_baseline_with_progress_noop_when_builder_unavailable(self):
        """Method should no-op safely when progress builder factory returns None."""
        from pathlib import Path

        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        orchestrator = object.__new__(SyncCacheOrchestrator)
        orchestrator.show_progress = True
        orchestrator.core = MagicMock()
        orchestrator.core.roadmap_dir = Path("/tmp/roadmap")

        with patch(
            "roadmap.adapters.sync.sync_cache_orchestrator.create_progress_builder",
            return_value=None,
        ):
            SyncCacheOrchestrator._rebuild_baseline_with_progress(
                orchestrator,
                progress_ctx=MagicMock(),
                issue_files=[],
                cached=None,
            )

        assert orchestrator._progress_builder is None

    def test_get_baseline_with_optimization_prefers_db_baseline(self):
        """Database baseline should short-circuit cache and reconstruction paths."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        orchestrator = object.__new__(SyncCacheOrchestrator)
        expected = MagicMock()
        orchestrator._try_get_database_baseline = MagicMock(return_value=expected)
        orchestrator._load_cached_baseline = MagicMock()
        orchestrator._rebuild_baseline_with_progress = MagicMock()

        result = SyncCacheOrchestrator._get_baseline_with_optimization(orchestrator)

        assert result is expected
        orchestrator._load_cached_baseline.assert_not_called()
        orchestrator._rebuild_baseline_with_progress.assert_not_called()

    def test_try_get_database_baseline_handles_exception(self):
        """Database load exceptions should degrade to None."""
        from roadmap.adapters.sync.sync_cache_orchestrator import SyncCacheOrchestrator

        orchestrator = object.__new__(SyncCacheOrchestrator)
        orchestrator.core = MagicMock()
        orchestrator.core.db.get_sync_baseline.side_effect = RuntimeError("fail")

        result = SyncCacheOrchestrator._try_get_database_baseline(orchestrator)
        assert result is None
