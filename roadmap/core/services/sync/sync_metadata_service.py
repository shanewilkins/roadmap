"""Sync metadata service for tracking issue sync history and statistics."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from roadmap.core.domain import Issue

logger = structlog.get_logger()


@dataclass
class SyncRecord:
    """Record of a single sync operation for an issue."""

    sync_timestamp: str  # ISO format
    success: bool
    local_changes: dict[str, Any] | None = None
    github_changes: dict[str, Any] | None = None
    conflict_resolution: str | None = None  # "local", "github", or None
    error_message: str | None = None
    milestone_dependencies: list[str] = field(
        default_factory=list
    )  # Milestone IDs this sync depended on
    dependency_resolution_time: float | None = (
        None  # Time spent resolving dependencies in seconds
    )


@dataclass
class SyncMetadata:
    """Metadata tracking for issue synchronization."""

    issue_id: str
    github_issue_id: int
    last_sync_time: str | None = None
    sync_count: int = 0
    successful_syncs: int = 0
    last_sync_status: str = "never"  # "success", "conflict", "error", "never"
    sync_history: list[SyncRecord] = field(default_factory=list)
    milestone_sync_count: int = 0  # Number of syncs involving milestones
    last_milestone_resolution_time: float | None = (
        None  # Last dependency resolution time
    )
    circular_dependencies_detected: int = 0  # Count of circular dependency detections

    def add_sync_record(self, record: SyncRecord) -> None:
        """Add a sync record to history."""
        self.sync_history.append(record)
        self.sync_count += 1
        self.last_sync_time = record.sync_timestamp

        if record.success:
            self.successful_syncs += 1
            self.last_sync_status = "success"
        elif record.conflict_resolution:
            self.last_sync_status = "conflict"
        else:
            self.last_sync_status = "error"

        # Track milestone-specific metrics
        if record.milestone_dependencies:
            self.milestone_sync_count += 1
        if record.dependency_resolution_time is not None:
            self.last_milestone_resolution_time = record.dependency_resolution_time

    def get_success_rate(self) -> float:
        """Calculate sync success rate."""
        if self.sync_count == 0:
            return 0.0
        return (self.successful_syncs / self.sync_count) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "issue_id": self.issue_id,
            "github_issue_id": self.github_issue_id,
            "last_sync_time": self.last_sync_time,
            "sync_count": self.sync_count,
            "successful_syncs": self.successful_syncs,
            "last_sync_status": self.last_sync_status,
            "milestone_sync_count": self.milestone_sync_count,
            "last_milestone_resolution_time": self.last_milestone_resolution_time,
            "circular_dependencies_detected": self.circular_dependencies_detected,
            "sync_history": [
                {
                    "sync_timestamp": r.sync_timestamp,
                    "success": r.success,
                    "local_changes": r.local_changes,
                    "github_changes": r.github_changes,
                    "conflict_resolution": r.conflict_resolution,
                    "error_message": r.error_message,
                    "milestone_dependencies": r.milestone_dependencies,
                    "dependency_resolution_time": r.dependency_resolution_time,
                }
                for r in self.sync_history
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncMetadata":
        """Create from dictionary (loaded from storage)."""
        history = [
            SyncRecord(
                sync_timestamp=r["sync_timestamp"],
                success=r["success"],
                local_changes=r.get("local_changes"),
                github_changes=r.get("github_changes"),
                conflict_resolution=r.get("conflict_resolution"),
                error_message=r.get("error_message"),
                milestone_dependencies=r.get("milestone_dependencies", []),
                dependency_resolution_time=r.get("dependency_resolution_time"),
            )
            for r in data.get("sync_history", [])
        ]
        return cls(
            issue_id=data["issue_id"],
            github_issue_id=data["github_issue_id"],
            last_sync_time=data.get("last_sync_time"),
            sync_count=data.get("sync_count", 0),
            successful_syncs=data.get("successful_syncs", 0),
            last_sync_status=data.get("last_sync_status", "never"),
            milestone_sync_count=data.get("milestone_sync_count", 0),
            last_milestone_resolution_time=data.get("last_milestone_resolution_time"),
            circular_dependencies_detected=data.get(
                "circular_dependencies_detected", 0
            ),
            sync_history=history,
        )


class SyncMetadataService:
    """Service for managing sync metadata persistence and queries."""

    def __init__(self, core):
        """Initialize metadata service.

        Args:
            core: RoadmapCore instance
        """
        self.core = core
        # In-memory cache of metadata (keyed by issue_id)
        self._cache: dict[str, SyncMetadata] = {}

    def get_metadata(self, issue: Issue) -> SyncMetadata:
        """Get sync metadata for an issue.

        Args:
            issue: Issue to get metadata for

        Returns:
            SyncMetadata for the issue
        """
        if issue.id in self._cache:
            return self._cache[issue.id]

        # Try to load from issue's github_sync_metadata field
        if hasattr(issue, "github_sync_metadata") and issue.github_sync_metadata:
            try:
                metadata = SyncMetadata.from_dict(issue.github_sync_metadata)
                self._cache[issue.id] = metadata
                return metadata
            except Exception as e:
                logger.debug(
                    "sync_metadata_deserialization_failed",
                    operation="load_from_cache",
                    issue_id=issue.id,
                    error=str(e),
                    action="Creating new metadata",
                )

        # Create new metadata
        github_id = getattr(issue, "github_issue", None)
        metadata = SyncMetadata(
            issue_id=issue.id,
            github_issue_id=github_id or 0,
        )
        self._cache[issue.id] = metadata
        return metadata

    def record_sync(
        self,
        issue: Issue,
        success: bool,
        local_changes: dict[str, Any] | None = None,
        github_changes: dict[str, Any] | None = None,
        conflict_resolution: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Record a sync operation for an issue.

        Args:
            issue: Issue that was synced
            success: Whether sync succeeded
            local_changes: Local changes detected
            github_changes: GitHub changes detected
            conflict_resolution: How conflicts were resolved
            error_message: Error message if sync failed
        """
        metadata = self.get_metadata(issue)

        record = SyncRecord(
            sync_timestamp=datetime.now(UTC).isoformat(),
            success=success,
            local_changes=local_changes,
            github_changes=github_changes,
            conflict_resolution=conflict_resolution,
            error_message=error_message,
        )
        metadata.add_sync_record(record)

        # Persist to issue
        if not hasattr(issue, "github_sync_metadata"):
            issue.github_sync_metadata = {}
        issue.github_sync_metadata = metadata.to_dict()

    def get_sync_history(self, issue: Issue, limit: int = 10) -> list[SyncRecord]:
        """Get sync history for an issue.

        Args:
            issue: Issue to get history for
            limit: Maximum number of records to return

        Returns:
            List of sync records (most recent first)
        """
        metadata = self.get_metadata(issue)
        return list(reversed(metadata.sync_history))[:limit]

    def get_statistics(self, issues: list[Issue]) -> dict[str, Any]:
        """Get aggregate sync statistics across issues.

        Args:
            issues: List of issues to analyze

        Returns:
            Dictionary with statistics
        """
        total_issues = len(issues)
        total_syncs = 0
        successful_syncs = 0
        never_synced = 0
        total_conflicts = 0

        for issue in issues:
            metadata = self.get_metadata(issue)
            total_syncs += metadata.sync_count
            successful_syncs += metadata.successful_syncs

            if metadata.sync_count == 0:
                never_synced += 1

            total_conflicts += sum(
                1 for record in metadata.sync_history if record.conflict_resolution
            )

        return {
            "total_issues": total_issues,
            "never_synced": never_synced,
            "total_sync_attempts": total_syncs,
            "successful_syncs": successful_syncs,
            "total_conflicts": total_conflicts,
            "success_rate": (
                (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0
            ),
            "conflict_rate": (
                (total_conflicts / total_syncs * 100) if total_syncs > 0 else 0
            ),
        }
