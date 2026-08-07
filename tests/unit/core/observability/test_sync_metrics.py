"""Tests for sync metrics and observability tracking."""

from datetime import UTC, datetime, timedelta

import pytest

from roadmap.core.observability.sync_metrics import (
    SyncMetrics,
    SyncObservability,
    get_observability,
    set_observability,
)


class TestSyncMetrics:
    """Test suite for SyncMetrics dataclass."""

    def test_metrics_initialization_defaults(self):
        """Test metrics initialize with proper defaults."""
        metrics = SyncMetrics()
        assert metrics.backend_type == ""
        assert metrics.duration_seconds == 0.0
        assert metrics.local_issues_before_dedup == 0
        assert metrics.remote_issues_before_dedup == 0
        assert metrics.duplicates_detected == 0
        assert metrics.issues_fetched == 0
        assert metrics.conflicts_detected == 0
        assert metrics.errors_count == 0
        assert metrics.cache_hit_rate == 0.0
        assert metrics.circuit_breaker_state == "closed"

    def test_metrics_initialization_with_values(self):
        """Test metrics can be initialized with custom values."""
        metrics = SyncMetrics(
            backend_type="github",
            issues_fetched=100,
            duplicates_detected=10,
        )
        assert metrics.backend_type == "github"
        assert metrics.issues_fetched == 100
        assert metrics.duplicates_detected == 10

    def test_metrics_calculate_local_reduction_percentage(self):
        """Test local deduplication reduction calculation."""
        metrics = SyncMetrics(
            local_issues_before_dedup=1828,
            local_issues_after_dedup=99,
        )
        metrics.calculate_reductions()
        expected = ((1828 - 99) / 1828) * 100
        assert abs(metrics.local_dedup_reduction_pct - expected) < 0.01

    def test_metrics_calculate_remote_reduction_percentage(self):
        """Test remote deduplication reduction calculation."""
        metrics = SyncMetrics(
            remote_issues_before_dedup=1869,
            remote_issues_after_dedup=99,
        )
        metrics.calculate_reductions()
        expected = ((1869 - 99) / 1869) * 100
        assert abs(metrics.remote_dedup_reduction_pct - expected) < 0.01

    def test_metrics_calculate_reductions_zero_before(self):
        """Test reduction calculation handles zero before values."""
        metrics = SyncMetrics(
            local_issues_before_dedup=0,
            local_issues_after_dedup=0,
        )
        metrics.calculate_reductions()
        assert metrics.local_dedup_reduction_pct == 0.0

    def test_metrics_to_dict_complete(self):
        """Test converting metrics to dictionary."""
        metrics = SyncMetrics(
            operation_id="test-op-123",
            backend_type="github",
            duration_seconds=2.5,
            issues_fetched=100,
        )
        metrics_dict = metrics.to_dict()

        assert metrics_dict["operation_id"] == "test-op-123"
        assert metrics_dict["backend_type"] == "github"
        assert metrics_dict["duration_seconds"] == 2.5
        assert metrics_dict["issues_fetched"] == 100

    def test_metrics_operation_id_uniqueness(self):
        """Test that each metrics instance gets unique operation ID."""
        m1 = SyncMetrics()
        m2 = SyncMetrics()
        assert m1.operation_id != m2.operation_id


class TestSyncObservability:
    """Test suite for SyncObservability service."""

    @pytest.fixture
    def observability(self):
        """Create fresh observability instance for each test."""
        return SyncObservability()

    def test_start_operation_returns_operation_id(self, observability):
        """Test starting an operation returns operation ID."""
        op_id = observability.start_operation("github")
        assert op_id is not None
        assert isinstance(op_id, str)
        assert len(op_id) > 0

    def test_start_operation_creates_metrics(self, observability):
        """Test starting operation creates metrics entry."""
        op_id = observability.start_operation("github")
        metrics = observability.get_metrics(op_id)

        assert metrics is not None
        assert metrics.operation_id == op_id
        assert metrics.backend_type == "github"

    def test_record_local_dedup(self, observability):
        """Test recording local deduplication metrics."""
        op_id = observability.start_operation("github")
        observability.record_local_dedup(op_id, before=1828, after=99, duration=0.26)

        metrics = observability.get_metrics(op_id)
        assert metrics.local_issues_before_dedup == 1828
        assert metrics.local_issues_after_dedup == 99
        assert metrics.local_dedup_phase_duration == 0.26

    def test_record_remote_dedup(self, observability):
        """Test recording remote deduplication metrics."""
        op_id = observability.start_operation("github")
        observability.record_remote_dedup(op_id, before=1869, after=99, duration=0.23)

        metrics = observability.get_metrics(op_id)
        assert metrics.remote_issues_before_dedup == 1869
        assert metrics.remote_issues_after_dedup == 99
        assert metrics.remote_dedup_phase_duration == 0.23

    def test_record_fetch(self, observability):
        """Test recording fetch operation metrics."""
        op_id = observability.start_operation("github")
        observability.record_fetch(op_id, count=1869, duration=0.3)

        metrics = observability.get_metrics(op_id)
        assert metrics.issues_fetched == 1869
        assert metrics.fetch_phase_duration == 0.3

    def test_record_push(self, observability):
        """Test recording push operation metrics."""
        op_id = observability.start_operation("github")
        observability.record_push(op_id, count=50, duration=0.5)

        metrics = observability.get_metrics(op_id)
        assert metrics.issues_pushed == 50
        assert metrics.push_phase_duration == 0.5

    def test_record_pull(self, observability):
        """Test recording pull operation metrics."""
        op_id = observability.start_operation("github")
        observability.record_pull(op_id, count=25, duration=0.2)

        metrics = observability.get_metrics(op_id)
        assert metrics.issues_pulled == 25
        assert metrics.pull_phase_duration == 0.2

    def test_record_conflict_single(self, observability):
        """Test recording single conflict."""
        op_id = observability.start_operation("github")
        observability.record_conflict(op_id)

        metrics = observability.get_metrics(op_id)
        assert metrics.conflicts_detected == 1

    def test_record_conflict_multiple(self, observability):
        """Test recording multiple conflicts."""
        op_id = observability.start_operation("github")
        observability.record_conflict(op_id, count=3, resolution_duration=0.5)

        metrics = observability.get_metrics(op_id)
        assert metrics.conflicts_detected == 3
        assert metrics.conflict_resolution_duration == 0.5

    def test_record_conflict_accumulates(self, observability):
        """Test that conflict recording accumulates."""
        op_id = observability.start_operation("github")
        observability.record_conflict(op_id, count=2)
        observability.record_conflict(op_id, count=3)

        metrics = observability.get_metrics(op_id)
        assert metrics.conflicts_detected == 5

    def test_record_duplicate_detected(self, observability):
        """Test recording duplicate detection."""
        op_id = observability.start_operation("github")
        observability.record_duplicate_detected(op_id, count=10)

        metrics = observability.get_metrics(op_id)
        assert metrics.duplicates_detected == 10

    def test_record_duplicate_resolved(self, observability):
        """Test recording duplicate resolution."""
        op_id = observability.start_operation("github")
        observability.record_duplicate_resolved(
            op_id,
            count=10,
            auto_resolved=8,
            deleted=2,
            archived=0,
        )

        metrics = observability.get_metrics(op_id)
        assert metrics.duplicates_auto_resolved == 8
        assert metrics.duplicates_manual_resolved == 2
        assert metrics.issues_deleted == 2
        assert metrics.issues_archived == 0

    def test_record_error(self, observability):
        """Test recording error metrics."""
        op_id = observability.start_operation("github")
        observability.record_error(op_id, "network_error", "Connection timeout")

        metrics = observability.get_metrics(op_id)
        assert metrics.errors_count == 1

    def test_record_error_accumulates(self, observability):
        """Test that errors accumulate."""
        op_id = observability.start_operation("github")
        observability.record_error(op_id, "error1")
        observability.record_error(op_id, "error2")
        observability.record_error(op_id, "error3")

        metrics = observability.get_metrics(op_id)
        assert metrics.errors_count == 3

    def test_record_phase_timing_analysis(self, observability):
        """Test recording analysis phase timing."""
        op_id = observability.start_operation("github")
        observability.record_phase_timing(op_id, "analysis", 0.5)

        metrics = observability.get_metrics(op_id)
        assert metrics.analysis_phase_duration == 0.5

    def test_record_phase_timing_merge(self, observability):
        """Test recording merge phase timing."""
        op_id = observability.start_operation("github")
        observability.record_phase_timing(op_id, "merge", 1.2)

        metrics = observability.get_metrics(op_id)
        assert metrics.merge_phase_duration == 1.2

    def test_record_cache_stats(self, observability):
        """Test recording cache statistics."""
        op_id = observability.start_operation("github")
        observability.record_cache_stats(op_id, hit_rate=0.85)

        metrics = observability.get_metrics(op_id)
        assert metrics.cache_hit_rate == 0.85

    def test_record_circuit_breaker_state(self, observability):
        """Test recording circuit breaker state."""
        op_id = observability.start_operation("github")
        observability.record_circuit_breaker_state(op_id, "half-open")

        metrics = observability.get_metrics(op_id)
        assert metrics.circuit_breaker_state == "half-open"

    def test_record_sync_links(self, observability):
        """Test recording sync link metrics."""
        op_id = observability.start_operation("github")
        observability.record_sync_links(op_id, created=99, orphaned=0)

        metrics = observability.get_metrics(op_id)
        assert metrics.sync_links_created == 99
        assert metrics.orphaned_links == 0

    def test_record_metadata_string(self, observability):
        """Test recording string metadata."""
        op_id = observability.start_operation("github")
        observability.record_metadata(op_id, "user_id", "user123")

        metrics = observability.get_metrics(op_id)
        assert metrics.metadata["user_id"] == "user123"

    def test_record_metadata_multiple(self, observability):
        """Test recording multiple metadata entries."""
        op_id = observability.start_operation("github")
        observability.record_metadata(op_id, "user_id", "user123")
        observability.record_metadata(op_id, "branch", "main")
        observability.record_metadata(op_id, "retry_count", 3)

        metrics = observability.get_metrics(op_id)
        assert metrics.metadata["user_id"] == "user123"
        assert metrics.metadata["branch"] == "main"
        assert metrics.metadata["retry_count"] == 3

    def test_finalize_sets_duration(self, observability):
        """Test finalize calculates total duration."""
        op_id = observability.start_operation("github")
        metrics = observability.get_metrics(op_id)
        original_start = metrics.start_time

        # Simulate some time passing
        metrics.start_time = original_start - timedelta(seconds=2.5)

        final_metrics = observability.finalize(op_id)
        assert final_metrics.duration_seconds > 0.0

    def test_finalize_returns_same_metrics(self, observability):
        """Test finalize returns the recorded metrics."""
        op_id = observability.start_operation("github")
        observability.record_fetch(op_id, 100, 0.5)

        final = observability.finalize(op_id)
        assert final.operation_id == op_id
        assert final.issues_fetched == 100

    def test_get_metrics_returns_none_for_unknown_op(self, observability):
        """Test get_metrics returns None for unknown operation."""
        metrics = observability.get_metrics("unknown-op-id")
        assert metrics is None

    def test_multiple_concurrent_operations(self, observability):
        """Test tracking multiple concurrent operations."""
        op1 = observability.start_operation("github")
        op2 = observability.start_operation("vanilla_git")

        observability.record_fetch(op1, 100, 0.5)
        observability.record_fetch(op2, 50, 0.3)

        m1 = observability.get_metrics(op1)
        m2 = observability.get_metrics(op2)

        assert m1.issues_fetched == 100
        assert m2.issues_fetched == 50
        assert m1.backend_type == "github"
        assert m2.backend_type == "vanilla_git"

    def test_clear_old_operations(self, observability):
        """Test clearing old operations."""
        op1 = observability.start_operation("github")

        # Manually set old start time
        observability.get_metrics(op1).start_time = datetime.now(UTC) - timedelta(
            hours=2
        )

        cleared = observability.clear_old_operations(max_age_seconds=3600)
        assert cleared == 1
        assert observability.get_metrics(op1) is None

    def test_clear_old_operations_preserves_recent(self, observability):
        """Test that clear_old_operations preserves recent operations."""
        op_old = observability.start_operation("github")
        op_new = observability.start_operation("github")

        # Only mark one as old
        observability.get_metrics(op_old).start_time = datetime.now(UTC) - timedelta(
            hours=2
        )

        cleared = observability.clear_old_operations(max_age_seconds=3600)
        assert cleared == 1
        assert observability.get_metrics(op_old) is None
        assert observability.get_metrics(op_new) is not None


class TestGlobalObservability:
    """Test suite for global observability instance management."""

    def test_get_observability_returns_singleton(self):
        """Test get_observability returns singleton instance."""
        obs1 = get_observability()
        obs2 = get_observability()
        assert obs1 is obs2

    def test_set_observability_replaces_instance(self):
        """Test set_observability replaces the global instance."""
        original = get_observability()
        new_obs = SyncObservability()

        set_observability(new_obs)
        assert get_observability() is new_obs
        assert get_observability() is not original

        # Restore for other tests
        set_observability(original)


class TestSyncMetricsIntegration:
    """Integration tests for complete sync metric workflows."""

    def test_complete_sync_workflow_metrics(self):
        """Test metrics for a complete sync workflow."""
        obs = SyncObservability()

        # Start operation
        op_id = obs.start_operation("github")

        # Record deduplication
        obs.record_local_dedup(op_id, 1828, 99, 0.26)
        obs.record_remote_dedup(op_id, 1869, 99, 0.23)

        # Record fetch
        obs.record_fetch(op_id, 99, 0.3)

        # Record conflicts
        obs.record_conflict(op_id, count=2, resolution_duration=0.1)

        # Record duplicate handling
        obs.record_duplicate_detected(op_id, 5)
        obs.record_duplicate_resolved(op_id, 5, 3, 2, 0)

        # Record sync operations
        obs.record_push(op_id, 50, 0.5)
        obs.record_pull(op_id, 25, 0.2)

        # Record phase timing
        obs.record_phase_timing(op_id, "analysis", 0.5)
        obs.record_phase_timing(op_id, "merge", 1.2)

        # Record performance metrics
        obs.record_cache_stats(op_id, 0.85)
        obs.record_circuit_breaker_state(op_id, "closed")

        # Record sync links
        obs.record_sync_links(op_id, 99, 0)

        # Finalize
        final = obs.finalize(op_id)

        # Verify all metrics were recorded
        assert final.local_issues_before_dedup == 1828
        assert final.remote_issues_before_dedup == 1869
        assert final.issues_fetched == 99
        assert final.conflicts_detected == 2
        assert final.duplicates_detected == 5
        assert final.duplicates_auto_resolved == 3
        assert final.issues_deleted == 2
        assert final.issues_pushed == 50
        assert final.issues_pulled == 25
        assert final.analysis_phase_duration == 0.5
        assert final.merge_phase_duration == 1.2
        assert final.cache_hit_rate == 0.85
        assert final.circuit_breaker_state == "closed"
        assert final.sync_links_created == 99
        assert final.duration_seconds > 0

    def test_metrics_to_dict_complete_workflow(self):
        """Test converting complete workflow metrics to dictionary."""
        obs = SyncObservability()
        op_id = obs.start_operation("github")

        obs.record_local_dedup(op_id, 1828, 99, 0.26)
        obs.record_fetch(op_id, 99, 0.3)
        obs.record_duplicate_detected(op_id, 5)

        final = obs.finalize(op_id)
        metrics_dict = final.to_dict()

        assert metrics_dict["operation_id"] == op_id
        assert metrics_dict["backend_type"] == "github"
        assert metrics_dict["local_issues_before_dedup"] == 1828
        assert metrics_dict["issues_fetched"] == 99
        assert metrics_dict["duplicates_detected"] == 5
        assert "duration_seconds" in metrics_dict
