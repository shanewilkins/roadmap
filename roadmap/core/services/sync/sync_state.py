"""Sync state models for tracking local and remote state."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class IssueBaseState:
    """Base state of an issue from sync perspective."""

    id: str
    status: str
    assignee: str | None = None
    labels: list[str] = field(default_factory=list)
    description: str = ""
    title: str = ""
    headline: str = ""
    content: str = ""
    priority: int = 0
    blocked_by: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived: bool = False
    custom_fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for comparison."""
        return {
            "id": self.id,
            "status": self.status,
            "assignee": self.assignee,
            "labels": self.labels,
            "description": self.description,
            "title": self.title,
            "headline": self.headline,
            "content": self.content,
            "priority": self.priority,
            "blocked_by": self.blocked_by,
            "blocks": self.blocks,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "archived": self.archived,
            "custom_fields": self.custom_fields,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IssueBaseState":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SyncState:
    """Current sync state of the system."""

    local_issues: dict[str, IssueBaseState] = field(default_factory=dict)
    remote_issues: dict[str, IssueBaseState] = field(default_factory=dict)
    base_issues: dict[str, IssueBaseState] = field(default_factory=dict)
    last_sync_time: datetime | None = None
    sync_in_progress: bool = False
    local_deleted_ids: set[str] = field(default_factory=set)
    remote_deleted_ids: set[str] = field(default_factory=set)

    def get_issue_dict(self, source: str) -> dict[str, dict[str, Any]]:
        """Get issues as dictionary of dicts for merging."""
        if source == "local":
            issues = self.local_issues
        elif source == "remote":
            issues = self.remote_issues
        elif source == "base":
            issues = self.base_issues
        else:
            raise ValueError(f"Unknown source: {source}")

        return {issue_id: state.to_dict() for issue_id, state in issues.items()}

    def add_issue(
        self,
        source: str,
        issue: IssueBaseState,
    ) -> None:
        """Add or update an issue in the specified source."""
        if source == "local":
            self.local_issues[issue.id] = issue
        elif source == "remote":
            self.remote_issues[issue.id] = issue
        elif source == "base":
            self.base_issues[issue.id] = issue
        else:
            raise ValueError(f"Unknown source: {source}")

    def get_issue(self, source: str, issue_id: str) -> IssueBaseState | None:
        """Get a specific issue from a source."""
        if source == "local":
            return self.local_issues.get(issue_id)
        elif source == "remote":
            return self.remote_issues.get(issue_id)
        elif source == "base":
            return self.base_issues.get(issue_id)
        else:
            raise ValueError(f"Unknown source: {source}")

    def mark_deleted(self, source: str, issue_id: str) -> None:
        """Mark an issue as deleted in the specified source."""
        if source == "local":
            self.local_deleted_ids.add(issue_id)
            if issue_id in self.local_issues:
                del self.local_issues[issue_id]
        elif source == "remote":
            self.remote_deleted_ids.add(issue_id)
            if issue_id in self.remote_issues:
                del self.remote_issues[issue_id]
        else:
            raise ValueError(f"Unknown source: {source}")

    def mark_synced(self) -> None:
        """Mark sync as complete."""
        self.sync_in_progress = False
        self.last_sync_time = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "local_issues": {
                issue_id: state.to_dict()
                for issue_id, state in self.local_issues.items()
            },
            "remote_issues": {
                issue_id: state.to_dict()
                for issue_id, state in self.remote_issues.items()
            },
            "base_issues": {
                issue_id: state.to_dict()
                for issue_id, state in self.base_issues.items()
            },
            "last_sync_time": self.last_sync_time.isoformat()
            if self.last_sync_time
            else None,
            "sync_in_progress": self.sync_in_progress,
            "local_deleted_ids": list(self.local_deleted_ids),
            "remote_deleted_ids": list(self.remote_deleted_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncState":
        """Create from dictionary."""
        local_issues = {
            issue_id: IssueBaseState.from_dict(state)
            for issue_id, state in data.get("local_issues", {}).items()
        }
        remote_issues = {
            issue_id: IssueBaseState.from_dict(state)
            for issue_id, state in data.get("remote_issues", {}).items()
        }
        base_issues = {
            issue_id: IssueBaseState.from_dict(state)
            for issue_id, state in data.get("base_issues", {}).items()
        }
        last_sync_time = None
        if data.get("last_sync_time"):
            last_sync_time = datetime.fromisoformat(data["last_sync_time"])

        return cls(
            local_issues=local_issues,
            remote_issues=remote_issues,
            base_issues=base_issues,
            last_sync_time=last_sync_time,
            sync_in_progress=data.get("sync_in_progress", False),
            local_deleted_ids=set(data.get("local_deleted_ids", [])),
            remote_deleted_ids=set(data.get("remote_deleted_ids", [])),
        )
