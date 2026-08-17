"""Framework-free domain value types."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import uuid4

from .failures import InvalidValue


class EntityId(str):
    """Opaque stable identity; existing identifiers remain byte-for-byte intact."""

    def __new__(cls, value: str) -> Self:
        if not value or value != value.strip() or any(c in value for c in "/\\\0\r\n"):
            raise InvalidValue("entity ID must be non-empty, trimmed, and path-safe")
        return str.__new__(cls, value)

    @classmethod
    def new(cls) -> "EntityId":
        return cls(str(uuid4()))


class RequiredText(str):
    """Trimmed non-empty user text."""

    def __new__(cls, value: str) -> Self:
        if not value or value != value.strip() or any(c in value for c in "\0\r\n"):
            raise InvalidValue("required text must be non-empty and single-line")
        return str.__new__(cls, value)


class Title(RequiredText):
    """Issue title."""


class Name(RequiredText):
    """Project or milestone name."""


@dataclass(frozen=True, slots=True, order=True)
class Timestamp:
    """Timezone-aware instant supplied by an application clock."""

    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is None or self.value.utcoffset() is None:
            raise InvalidValue("timestamp must include a UTC offset")


class Priority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueType(StrEnum):
    FEATURE = "feature"
    BUG = "bug"
    OTHER = "other"


class IssueStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in-progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    CLOSED = "closed"


class MilestoneStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class ProjectStatus(StrEnum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on-hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RetentionState(StrEnum):
    VISIBLE = "visible"
    ARCHIVED = "archived"
    PURGED = "purged"


@dataclass(frozen=True, slots=True)
class IssueRelations:
    milestone_id: EntityId | None = None
    depends_on: tuple[EntityId, ...] = ()
    blocks: tuple[EntityId, ...] = ()

    def validate_for(self, issue_id: EntityId) -> None:
        values = self.depends_on + self.blocks
        if issue_id in values or len(values) != len(set(values)):
            raise InvalidValue(
                "issue relationships must be unique and cannot reference self"
            )


@dataclass(frozen=True, slots=True)
class MilestoneRelation:
    project_id: EntityId | None = None


@dataclass(frozen=True, slots=True)
class ProjectRelations:
    milestone_ids: tuple[EntityId, ...] = ()

    def __post_init__(self) -> None:
        if len(self.milestone_ids) != len(set(self.milestone_ids)):
            raise InvalidValue("project milestone relationships must be unique")
