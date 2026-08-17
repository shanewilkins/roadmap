"""Framework-neutral request and response data."""

from dataclasses import dataclass

from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueType,
    Priority,
    Timestamp,
    Title,
)


@dataclass(frozen=True, slots=True)
class IssueDraft:
    title: Title
    priority: Priority = Priority.MEDIUM
    issue_type: IssueType = IssueType.OTHER
    relations: IssueRelations = IssueRelations()
    headline: str = ""
    content: str = ""


@dataclass(frozen=True, slots=True)
class MutationReceipt:
    entity_id: EntityId
    updated: Timestamp
    projection_stale: bool = False


@dataclass(frozen=True, slots=True)
class GitSnapshot:
    branch: str | None
    head: str | None
    changed_paths: tuple[str, ...]
