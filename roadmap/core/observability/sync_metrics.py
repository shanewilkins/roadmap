"""Comprehensive metrics tracking for sync operations.

Tracks all aspects of sync including:
- Issue deduplication metrics (local, remote, cross-set)
- Data fetching and syncing metrics
- Conflict detection and resolution
- Duplicate detection and resolution
- Cache hit rates and circuit breaker state
- Phase timing and performance breakdown
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class SyncMetrics:
    """Comprehensive metrics for a sync operation."""

    # Operation identification
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    backend_type: str = ""  # "github", "vanilla_git", etc.
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Overall timing
    duration_seconds: float = 0.0

    # Deduplication metrics - LOCAL
    local_issues_before_dedup: int = 0
    local_issues_after_dedup: int = 0
    local_dedup_reduction_pct: float = 0.0
    local_dedup_phase_duration: float = 0.0

    # Deduplication metrics - REMOTE
    remote_issues_before_dedup: int = 0
    remote_issues_after_dedup: int = 0
    remote_dedup_reduction_pct: float = 0.0
    remote_dedup_phase_duration: float = 0.0

    # Deduplication metrics - CROSS-SET
    cross_set_duplicates_detected: int = 0

    # Duplicate resolution metrics
    duplicates_detected: int = 0
    duplicates_auto_resolved: int = 0
    duplicates_manual_resolved: int = 0
    issues_deleted: int = 0  # Hard deleted (ID collisions)
    issues_archived: int = 0  # Soft deleted (fuzzy matches)

    # Sync operations
    issues_fetched: int = 0
    fetch_phase_duration: float = 0.0
    issues_pushed: int = 0
    push_phase_duration: float = 0.0
    issues_pulled: int = 0
    pull_phase_duration: float = 0.0

    # Conflict and error tracking
    conflicts_detected: int = 0
    conflict_resolution_duration: float = 0.0
    errors_count: int = 0

    # Performance metrics
    cache_hit_rate: float = 0.0
    circuit_breaker_state: str = "closed"

    # Phase timing
    analysis_phase_duration: float = 0.0
    merge_phase_duration: float = 0.0

    # Sync link metrics
    sync_links_created: int = 0
    orphaned_links: int = 0

    # Custom metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def calculate_reductions(self) -> None:
        """Calculate deduplication reduction percentages."""
        if self.local_issues_before_dedup > 0:
            self.local_dedup_reduction_pct = (
                ((self.local_issues_before_dedup - self.local_issues_after_dedup) /
                 self.local_issues_before_dedup) * 100
            )

        if self.remote_issues_before_dedup > 0:
            self.remote_dedup_reduction_pct = (
                ((self.remote_issues_before_dedup - self.remote_issues_after_dedup) /
                 self.remote_issues_before_dedup) * 100
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for storage."""
        return {
            "operation_id": self.operation_id,
            "backend_type": self.backend_type,
            "start_time": self.start_time.isoformat(),
            "duration_seconds": self.duration_seconds,
            # Dedup - Local
            "local_issues_before_dedup": self.local_issues_before_dedup,
            "local_issues_after_dedup": self.local_issues_after_dedup,
            "local_dedup_reduction_pct": self.local_dedup_reduction_pct,
            "local_dedup_phase_duration": self.local_dedup_phase_duration,
            # Dedup - Remote
            "remote_issues_before_dedup": self.remote_issues_before_dedup,
            "remote_issues_after_dedup": self.remote_issues_after_dedup,
            "remote_dedup_reduction_pct": self.remote_dedup_reduction_pct,
            "remote_dedup_phase_duration": self.remote_dedup_phase_duration,
            # Dedup - Cross-set
            "cross_set_duplicates_detected": self.cross_set_duplicates_detected,
            # Duplicate resolution
            "duplicates_detected": self.duplicates_detected,
            "duplicates_auto_resolved": self.duplicates_auto_resolved,
            "duplicates_manual_resolved": self.duplicates_manual_resolved,
            "issues_deleted": self.issues_deleted,
            "issues_archived": self.issues_archived,
            # Sync operations
            "issues_fetched": self.issues_fetched,
            "fetch_phase_duration": self.fetch_phase_duration,
            "issues_pushed": self.issues_pushed,
            "push_phase_duration": self.push_phase_duration,
            "issues_pulled": self.issues_pulled,
            "pull_phase_duration": self.pull_phase_duration,
            # Conflicts/errors
            "conflicts_detected": self.conflicts_detected,
            "conflict_resolution_duration": self.conflict_resolution_duration,
            "errors_count": self.errors_count,
            # Performance
            "cache_hit_rate": self.cache_hit_rate,
            "circuit_breaker_state": self.circuit_breaker_state,
            # Phase timing
            "analysis_phase_duration": self.analysis_phase_duration,
            "merge_phase_duration": self.merge_phase_duration,
            # Sync links
            "sync_links_created": self.sync_links_created,
            "orphaned_links": self.orphaned_links,
            # Metadata
            "metadata": self.metadata,
        }


class SyncObservability:
    """Service for tracking and reporting sync metrics.

    Provides methods to record metrics at various stages of sync
    and generates comprehensive reports for observability.
    """

    def __init__(self):
        """Initialize observability tracker."""
        self._operations: dict[str, SyncMetrics] = {}
        self._logger = logger

    def start_operation(self, backend_type: str) -> str:
        """Start tracking a sync operation.

        Args:
            backend_type: Type of backend (e.g., "github", "vanilla_git")

        Returns:
            operation_id for later reference
        """
        metrics = SyncMetrics(backend_type=backend_type)
        self._operations[metrics.operation_id] = metrics
        self._logger.info(
            "sync_operation_started",
            operation_id=metrics.operation_id,
            backend_type=backend_type,
        )
        return metrics.operation_id

    def record_local_dedup(
        self,
        operation_id: str,
        before: int,
        after: int,
        duration: float,
    ) -> None:
        """Record local issue deduplication metrics.

        Args:
            operation_id: ID of the sync operation
            before: Number of issues before deduplication
            after: Number of issues after deduplication
            duration: Time taken for deduplication (seconds)
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.local_issues_before_dedup = before
        metrics.local_issues_after_dedup = after
        metrics.local_dedup_phase_duration = duration
        metrics.calculate_reductions()

        self._logger.info(
            "local_dedup_recorded",
            operation_id=operation_id,
            before=before,
            after=after,
            reduction_pct=metrics.local_dedup_reduction_pct,
            duration_seconds=duration,
        )

    def record_remote_dedup(
        self,
        operation_id: str,
        before: int,
        after: int,
        duration: float,
    ) -> None:
        """Record remote issue deduplication metrics.

        Args:
            operation_id: ID of the sync operation
            before: Number of issues before deduplication
            after: Number of issues after deduplication
            duration: Time taken for deduplication (seconds)
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.remote_issues_before_dedup = before
        metrics.remote_issues_after_dedup = after
        metrics.remote_dedup_phase_duration = duration
        metrics.calculate_reductions()

        self._logger.info(
            "remote_dedup_recorded",
            operation_id=operation_id,
            before=before,
            after=after,
            reduction_pct=metrics.remote_dedup_reduction_pct,
            duration_seconds=duration,
        )

    def record_cross_set_duplicates(
        self,
        operation_id: str,
        count: int,
    ) -> None:
        """Record cross-set duplicate detection metrics.

        Args:
            operation_id: ID of the sync operation
            count: Number of cross-set duplicates detected
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.cross_set_duplicates_detected = count
        self._logger.info(
            "cross_set_duplicates_recorded",
            operation_id=operation_id,
            count=count,
        )

    def record_fetch(
        self,
        operation_id: str,
        count: int,
        duration: float,
    ) -> None:
        """Record data fetch metrics.

        Args:
            operation_id: ID of the sync operation
            count: Number of issues fetched
            duration: Time taken to fetch (seconds)
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.issues_fetched = count
        metrics.fetch_phase_duration = duration

        self._logger.info(
            "fetch_recorded",
            operation_id=operation_id,
            issues_fetched=count,
            duration_seconds=duration,
        )

    def record_push(
        self,
        operation_id: str,
        count: int,
        duration: float,
    ) -> None:
        """Record push operation metrics.

        Args:
            operation_id: ID of the sync operation
            count: Number of issues pushed
            duration: Time taken for push (seconds)
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.issues_pushed = count
        metrics.push_phase_duration = duration

        self._logger.info(
            "push_recorded",
            operation_id=operation_id,
            issues_pushed=count,
            duration_seconds=duration,
        )

    def record_pull(
        self,
        operation_id: str,
        count: int,
        duration: float,
    ) -> None:
        """Record pull operation metrics.

        Args:
            operation_id: ID of the sync operation
            count: Number of issues pulled
            duration: Time taken for pull (seconds)
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.issues_pulled = count
        metrics.pull_phase_duration = duration

        self._logger.info(
            "pull_recorded",
            operation_id=operation_id,
            issues_pulled=count,
            duration_seconds=duration,
        )

    def record_conflict(
        self,
        operation_id: str,
        count: int = 1,
        resolution_duration: float = 0.0,
    ) -> None:
        """Record conflict detection metrics.

        Args:
            operation_id: ID of the sync operation
            count: Number of conflicts detected (default: 1)
            resolution_duration: Time taken to resolve conflicts (seconds)
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.conflicts_detected += count
        metrics.conflict_resolution_duration += resolution_duration

        self._logger.info(
            "conflict_recorded",
            operation_id=operation_id,
            count=count,
            resolution_duration_seconds=resolution_duration,
        )

    def record_duplicate_detected(
        self,
        operation_id: str,
        count: int = 1,
    ) -> None:
        """Record duplicate detection metrics.

        Args:
            operation_id: ID of the sync operation
            count: Number of duplicates detected (default: 1)
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.duplicates_detected += count
        self._logger.info(
            "duplicate_detected",
            operation_id=operation_id,
            count=count,
        )

    def record_duplicate_resolved(
        self,
        operation_id: str,
        count: int = 1,
        auto_resolved: int = 0,
        deleted: int = 0,
        archived: int = 0,
    ) -> None:
        """Record duplicate resolution metrics.

        Args:
            operation_id: ID of the sync operation
            count: Total number of duplicates resolved
            auto_resolved: Number auto-resolved
            deleted: Number hard-deleted
            archived: Number soft-archived
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.duplicates_auto_resolved += auto_resolved
        metrics.duplicates_manual_resolved += (count - auto_resolved)
        metrics.issues_deleted += deleted
        metrics.issues_archived += archived

        self._logger.info(
            "duplicate_resolved",
            operation_id=operation_id,
            total_count=count,
            auto_resolved=auto_resolved,
            manual_resolved=(count - auto_resolved),
            deleted=deleted,
            archived=archived,
        )

    def record_error(
        self,
        operation_id: str,
        error_type: str,
        error_message: str = "",
    ) -> None:
        """Record error metrics.

        Args:
            operation_id: ID of the sync operation
            error_type: Type of error that occurred
            error_message: Optional error message
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.errors_count += 1
        self._logger.warning(
            "sync_error_recorded",
            operation_id=operation_id,
            error_type=error_type,
            error_message=error_message,
        )

    def record_phase_timing(
        self,
        operation_id: str,
        phase_name: str,
        duration: float,
    ) -> None:
        """Record timing for a sync phase.

        Args:
            operation_id: ID of the sync operation
            phase_name: Name of the phase ("analysis", "merge", etc.)
            duration: Duration of the phase (seconds)
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        if phase_name == "analysis":
            metrics.analysis_phase_duration = duration
        elif phase_name == "merge":
            metrics.merge_phase_duration = duration

        self._logger.info(
            "phase_timing_recorded",
            operation_id=operation_id,
            phase_name=phase_name,
            duration_seconds=duration,
        )

    def record_cache_stats(
        self,
        operation_id: str,
        hit_rate: float,
    ) -> None:
        """Record cache performance metrics.

        Args:
            operation_id: ID of the sync operation
            hit_rate: Cache hit rate (0.0-1.0)
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.cache_hit_rate = hit_rate
        self._logger.info(
            "cache_stats_recorded",
            operation_id=operation_id,
            hit_rate=hit_rate,
        )

    def record_circuit_breaker_state(
        self,
        operation_id: str,
        state: str,
    ) -> None:
        """Record circuit breaker state metrics.

        Args:
            operation_id: ID of the sync operation
            state: State of the circuit breaker ("closed", "open", "half-open")
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.circuit_breaker_state = state
        self._logger.debug(
            "circuit_breaker_state_recorded",
            operation_id=operation_id,
            state=state,
        )

    def record_sync_links(
        self,
        operation_id: str,
        created_count: int,
        orphaned: int = 0,
    ) -> None:
        """Record sync link metrics.

        Args:
            operation_id: ID of the sync operation
            created_count: Number of sync links created
            orphaned: Number of orphaned links (default: 0)
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.sync_links_created = created_count
        metrics.orphaned_links = orphaned

        self._logger.info(
            "sync_links_recorded",
            operation_id=operation_id,
            created_count=created_count,
            orphaned=orphaned,
        )

    def record_metadata(
        self,
        operation_id: str,
        key: str,
        value: Any,
    ) -> None:
        """Record custom metadata.

        Args:
            operation_id: ID of the sync operation
            key: Metadata key
            value: Metadata value
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return

        metrics.metadata[key] = value

    def finalize(self, operation_id: str) -> SyncMetrics:
        """Finalize and return metrics for a completed operation.

        Args:
            operation_id: ID of the sync operation

        Returns:
            Completed SyncMetrics object
        """
        metrics = self._get_metrics(operation_id)
        if not metrics:
            return SyncMetrics()

        end_time = datetime.now(UTC)
        metrics.duration_seconds = (
            (end_time - metrics.start_time).total_seconds()
        )

        self._logger.info(
            "sync_operation_completed",
            operation_id=operation_id,
            duration_seconds=metrics.duration_seconds,
            issues_fetched=metrics.issues_fetched,
            issues_pushed=metrics.issues_pushed,
            issues_pulled=metrics.issues_pulled,
            conflicts_detected=metrics.conflicts_detected,
            duplicates_detected=metrics.duplicates_detected,
            errors_count=metrics.errors_count,
        )

        return metrics

    def get_metrics(self, operation_id: str) -> SyncMetrics | None:
        """Retrieve metrics for an operation.

        Args:
            operation_id: ID of the sync operation

        Returns:
            SyncMetrics if found, None otherwise
        """
        return self._get_metrics(operation_id)

    def _get_metrics(self, operation_id: str) -> SyncMetrics | None:
        """Internal method to get metrics by operation ID.

        Args:
            operation_id: ID of the sync operation

        Returns:
            SyncMetrics if found, None otherwise
        """
        return self._operations.get(operation_id)

    def clear_old_operations(self, max_age_seconds: float = 86400) -> int:
        """Clear metrics for operations older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age of operations to keep (default: 1 day)

        Returns:
            Number of operations cleared
        """
        now = datetime.now(UTC)
        to_remove = []

        for op_id, metrics in self._operations.items():
            age = (now - metrics.start_time).total_seconds()
            if age > max_age_seconds:
                to_remove.append(op_id)

        for op_id in to_remove:
            del self._operations[op_id]

        if to_remove:
            self._logger.info(
                "old_operations_cleared",
                count=len(to_remove),
                max_age_seconds=max_age_seconds,
            )

        return len(to_remove)


# Global instance for use throughout the application
_global_observability: SyncObservability | None = None


def get_observability() -> SyncObservability:
    """Get or create global observability instance.

    Returns:
        SyncObservability singleton
    """
    global _global_observability
    if _global_observability is None:
        _global_observability = SyncObservability()
    return _global_observability


def set_observability(observability: SyncObservability) -> None:
    """Set global observability instance (useful for testing).

    Args:
        observability: SyncObservability instance to use globally
    """
    global _global_observability
    _global_observability = observability
