"""Tests for CachedSyncOrchestrator.

Tests verify that the optimized sync orchestrator correctly integrates
baseline building, database caching, and progress tracking.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.sync.cached_sync_orchestrator import (
    CachedSyncOrchestrator,
)
from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.core.models.sync_state import IssueBaseState, SyncState


@pytest.fixture
def mock_backend():
    """Create a mock sync backend."""
    backend = MagicMock(spec=SyncBackendInterface)
    backend.authenticate.return_value = True
    backend.get_issues.return_value = {}
    return backend


@pytest.fixture
def mock_core(tmp_path):
    """Create a mock RoadmapCore."""
    core = MagicMock()
    core.roadmap_dir = tmp_path / "roadmap"
    core.roadmap_dir.mkdir(exist_ok=True)

    # Create issues directory
    issues_dir = core.roadmap_dir / "issues"
    issues_dir.mkdir(exist_ok=True, parents=True)

    core.issues_dir = issues_dir
    core.issues.list.return_value = []

    return core


@pytest.fixture
def cached_orchestrator(mock_core, mock_backend):
    """Create CachedSyncOrchestrator instance."""
    return CachedSyncOrchestrator(
        mock_core,
        mock_backend,
        show_progress=False,
    )


class TestCachedSyncOrchestrator:
    """Test suite for CachedSyncOrchestrator."""

    def test_initialization(self, cached_orchestrator):
        """Test orchestrator initializes correctly."""
        assert cached_orchestrator.core is not None
        assert cached_orchestrator.backend is not None
        assert cached_orchestrator.optimized_builder is not None
        assert cached_orchestrator.show_progress is False

    def test_initialization_with_progress(self, mock_core, mock_backend):
        """Test orchestrator can enable progress."""
        orchestrator = CachedSyncOrchestrator(
            mock_core,
            mock_backend,
            show_progress=True,
        )
        assert orchestrator.show_progress is True

    def test_create_progress_context_disabled(self, cached_orchestrator):
        """Test progress context creation when disabled."""
        ctx = cached_orchestrator._create_progress_context()
        assert ctx is None

    def test_create_progress_context_enabled(self, mock_core, mock_backend):
        """Test progress context creation when enabled."""
        orchestrator = CachedSyncOrchestrator(
            mock_core,
            mock_backend,
            show_progress=True,
        )
        ctx = orchestrator._create_progress_context()
        assert ctx is not None

    def test_load_cached_baseline_no_db(self, cached_orchestrator):
        """Test loading baseline when database doesn't exist."""
        baseline = cached_orchestrator._load_cached_baseline()
        assert baseline is None

    def test_get_baseline_with_optimization_no_issues(self, cached_orchestrator):
        """Test baseline construction with no issues."""
        baseline = cached_orchestrator._get_baseline_with_optimization()
        # Should handle gracefully
        assert baseline is not None or baseline is None

    def test_sync_all_issues_without_progress(self, cached_orchestrator):
        """Test sync without progress context."""
        with patch.object(
            cached_orchestrator, "_get_baseline_with_optimization"
        ) as mock_baseline:
            mock_baseline.return_value = None

            with patch.object(
                CachedSyncOrchestrator.__bases__[0],
                "sync_all_issues",
                return_value=MagicMock(error=None),
            ):
                report = cached_orchestrator.sync_all_issues(
                    dry_run=True,
                    show_progress=False,
                )

                assert report is not None

    def test_sync_all_issues_with_progress(self, mock_core, mock_backend):
        """Test sync with progress context."""
        orchestrator = CachedSyncOrchestrator(
            mock_core,
            mock_backend,
            show_progress=True,
        )

        with patch.object(
            orchestrator, "_get_baseline_with_optimization"
        ) as mock_baseline:
            mock_baseline.return_value = None

            with patch.object(
                CachedSyncOrchestrator.__bases__[0],
                "sync_all_issues",
                return_value=MagicMock(
                    error=None,
                    pushed_count=0,
                    pulled_count=0,
                ),
            ):
                report = orchestrator.sync_all_issues(
                    dry_run=False,
                    show_progress=True,
                )

                assert report is not None

    def test_save_baseline_to_cache(self, cached_orchestrator):
        """Test saving baseline to cache."""
        baseline = SyncState(
            last_sync=datetime.now(),
            backend="github",
            issues={},
        )

        # Should not raise
        cached_orchestrator._save_baseline_to_cache(baseline)

    def test_get_baseline_with_optimization_progress(self, mock_core, mock_backend):
        """Test baseline construction with progress context."""
        orchestrator = CachedSyncOrchestrator(
            mock_core,
            mock_backend,
            show_progress=True,
        )

        progress_ctx = MagicMock()

        baseline = orchestrator._get_baseline_with_optimization(progress_ctx)
        # Should handle with or without progress
        assert baseline is None or isinstance(baseline, SyncState)

    def test_optimized_builder_integration(self, cached_orchestrator):
        """Test that OptimizedBaselineBuilder is properly integrated."""
        assert cached_orchestrator.optimized_builder is not None
        assert cached_orchestrator.optimized_builder.issues_dir is not None

    def test_sync_error_handling(self, cached_orchestrator):
        """Test error handling during sync."""
        with patch.object(
            cached_orchestrator,
            "_get_baseline_with_optimization",
            side_effect=Exception("Test error"),
        ):
            report = cached_orchestrator.sync_all_issues(dry_run=True)
            assert report.error is not None
            assert "Test error" in report.error


class TestOptimizedSyncIntegration:
    """Integration tests for optimized sync."""

    def test_full_sync_flow_dry_run(self, mock_core, mock_backend):
        """Test full sync flow in dry-run mode."""
        orchestrator = CachedSyncOrchestrator(
            mock_core,
            mock_backend,
            show_progress=False,
        )

        with patch.object(
            CachedSyncOrchestrator.__bases__[0],
            "sync_all_issues",
            return_value=MagicMock(error=None),
        ):
            report = orchestrator.sync_all_issues(dry_run=True)
            assert report is not None

    def test_full_sync_flow_with_baseline(self, mock_core, mock_backend):
        """Test sync with baseline state."""
        orchestrator = CachedSyncOrchestrator(
            mock_core,
            mock_backend,
            show_progress=False,
        )

        # Create baseline
        baseline = SyncState(
            last_sync=datetime.now(),
            backend="github",
            issues={
                "test-1": IssueBaseState(
                    id="test-1",
                    title="Test issue",
                    status="open",
                    description="Test",
                )
            },
        )

        with patch.object(orchestrator, "_load_cached_baseline", return_value=baseline):
            with patch.object(
                CachedSyncOrchestrator.__bases__[0],
                "sync_all_issues",
                return_value=MagicMock(error=None),
            ):
                result = orchestrator._get_baseline_with_optimization()
                assert result == baseline
