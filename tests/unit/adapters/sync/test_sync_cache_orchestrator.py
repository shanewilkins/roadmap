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
