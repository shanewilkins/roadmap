"""Sync dataclasses - canonical representations for sync operations.

These dataclasses serve as the common currency between local state and remote state
during sync operations. Backends normalize their API responses into these types,
and the generic orchestrator works exclusively with them.

This ensures the core sync logic is completely backend-agnostic.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SyncIssue:
    """Canonical representation of an issue for sync operations.

    Used as the common currency between local and remote states.
    Backends normalize their API responses into this format.
    """

    # Core fields (present in all backends)
    id: str
    title: str
    status: str  # Normalized: "open", "closed", "in_progress", etc.

    # Optional fields (may not be present in all backends)
    description: str = ""
    assignee: str | None = None
    milestone: str | None = None
    labels: list[str] = field(default_factory=list)

    # Timing
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Backend tracking
    backend_name: str = "unknown"  # "github", "gitlab", "git", etc.
    backend_id: str | int | None = None  # Native backend ID
    remote_ids: dict[str, str | int] = field(
        default_factory=dict
    )  # All known remote IDs

    # Extensibility for backend-specific data
    custom_fields: dict[str, Any] = field(
        default_factory=dict
    )  # Jira-style custom fields
    raw_response: dict[str, Any] = field(default_factory=dict)  # Raw API response
    metadata: dict[str, Any] = field(default_factory=dict)  # Custom tracking data

    def __post_init__(self):
        """Validate sync issue data."""
        if not self.id:
            raise ValueError("SyncIssue.id is required")
        if not self.title:
            raise ValueError("SyncIssue.title is required")
        if not self.status:
            raise ValueError("SyncIssue.status is required")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncIssue":
        """Create from dictionary (e.g., from JSON/YAML)."""
        # Handle datetime strings
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        # Filter to only known fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


@dataclass
class SyncMilestone:
    """Canonical representation of a milestone for sync operations."""

    # Core fields
    id: str
    name: str
    status: str = "open"  # "open", "closed"

    # Optional fields
    description: str | None = None
    due_date: datetime | None = None

    # Backend tracking
    backend_name: str = "unknown"
    backend_id: str | int | None = None
    remote_ids: dict[str, str | int] = field(default_factory=dict)

    # Extensibility
    custom_fields: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate sync milestone data."""
        if not self.id:
            raise ValueError("SyncMilestone.id is required")
        if not self.name:
            raise ValueError("SyncMilestone.name is required")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncMilestone":
        """Create from dictionary."""
        if isinstance(data.get("due_date"), str):
            data["due_date"] = datetime.fromisoformat(data["due_date"])

        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


@dataclass
class SyncProject:
    """Canonical representation of a project for sync operations."""

    # Core fields
    id: str
    name: str

    # Optional fields
    description: str | None = None

    # Backend tracking
    backend_name: str = "unknown"
    backend_id: str | int | None = None
    remote_ids: dict[str, str | int] = field(default_factory=dict)

    # Extensibility
    custom_fields: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate sync project data."""
        if not self.id:
            raise ValueError("SyncProject.id is required")
        if not self.name:
            raise ValueError("SyncProject.name is required")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncProject":
        """Create from dictionary."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
