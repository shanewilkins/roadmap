"""Sync state model for tracking the agreed-upon state between syncs.

Stores the base state (from the last successful sync) which is used
for three-way merge during the next sync.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class IssueBaseState:
    """Represents the base (agreed-upon) state of a single issue.

    This is the snapshot taken after the last successful sync.
    Stored in .sync-state.json for use in three-way merge.
    """

    id: str
    status: str
    title: str  # Added: title is synced to remote, so track it
    assignee: str | None = None
    milestone: str | None = None
    headline: str = ""
    labels: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        data = asdict(self)
        data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "IssueBaseState":
        """Load from JSON dict."""
        data_copy = data.copy()
        if isinstance(data_copy.get("updated_at"), str):
            data_copy["updated_at"] = datetime.fromisoformat(data_copy["updated_at"])
        return cls(**data_copy)


@dataclass
class SyncState:
    """Represents the complete sync state (base snapshot from last successful sync).

    This is serialized to .sync-state.json in the .roadmap directory.
    It tracks the agreed-upon state of all issues after the last sync.
    """

    last_sync: datetime
    backend: str  # "github" or "git"
    issues: dict[str, IssueBaseState] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "last_sync": self.last_sync.isoformat(),
            "backend": self.backend,
            "issues": {
                issue_id: state.to_dict() for issue_id, state in self.issues.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncState":
        """Load from JSON dict."""
        last_sync = data["last_sync"]
        if isinstance(last_sync, str):
            last_sync = datetime.fromisoformat(last_sync)

        issues = {}
        for issue_id, issue_data in data.get("issues", {}).items():
            issues[issue_id] = IssueBaseState.from_dict(issue_data)

        return cls(
            last_sync=last_sync,
            backend=data["backend"],
            issues=issues,
        )

    def update_issue(self, issue_id: str, issue_state: IssueBaseState) -> None:
        """Update the base state for a single issue."""
        self.issues[issue_id] = issue_state
        self.last_sync = datetime.utcnow()

    def add_issue(self, issue_id: str, issue_state: IssueBaseState) -> None:
        """Add a new issue to the base state."""
        self.issues[issue_id] = issue_state

    def remove_issue(self, issue_id: str) -> None:
        """Remove an issue from the base state."""
        if issue_id in self.issues:
            del self.issues[issue_id]
