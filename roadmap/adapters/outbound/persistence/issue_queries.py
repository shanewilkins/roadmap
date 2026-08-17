"""Canonical issue query adapter with disposable SQLite candidate selection."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from roadmap.application.contracts import IssueCommentView, IssueQueryRecord
from roadmap.domain.aggregates import Issue, Milestone
from roadmap.domain.types import EntityId, MilestoneStatus, RetentionState, Timestamp

from .documents import DocumentEnvelope, DocumentError, DocumentRepository
from .projection import ProjectionError, SQLiteProjection


def _timestamp(value: Any, field: str) -> Timestamp:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise DocumentError(f"invalid {field} timestamp: {value}") from error
    else:
        raise DocumentError(f"missing {field} timestamp")
    try:
        return Timestamp(parsed)
    except ValueError as error:
        raise DocumentError(f"invalid {field} timestamp: {value}") from error


def _comment(value: Any) -> IssueCommentView:
    if not isinstance(value, dict):
        raise DocumentError("issue comment must be a mapping")
    try:
        return IssueCommentView(
            id=int(value["id"]),
            author=str(value["author"]),
            body=str(value["body"]),
            created_at=_timestamp(value.get("created_at"), "comment created_at"),
            updated_at=_timestamp(value.get("updated_at"), "comment updated_at"),
            in_reply_to=(
                int(value["in_reply_to"])
                if value.get("in_reply_to") is not None
                else None
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise DocumentError(f"invalid issue comment: {error}") from error


def _record(envelope: DocumentEnvelope) -> IssueQueryRecord:
    aggregate = envelope.aggregate
    if not isinstance(aggregate, Issue):
        raise DocumentError(f"expected issue document, got {envelope.kind}")
    raw_comments = envelope.extra_frontmatter.get("comments", [])
    if not isinstance(raw_comments, list):
        raise DocumentError("issue comments must be a list")
    raw_end = envelope.extra_frontmatter.get("actual_end_date")
    return IssueQueryRecord(
        issue=aggregate,
        comments=tuple(_comment(value) for value in raw_comments),
        actual_end_at=_timestamp(raw_end, "actual_end_date") if raw_end else None,
    )


class DocumentIssueQueries:
    """Read typed issue records from canonical documents."""

    def __init__(
        self, repository: DocumentRepository, projection: SQLiteProjection | None = None
    ):
        self._repository = repository
        self._projection = projection

    def list_issue_records(self) -> tuple[IssueQueryRecord, ...]:
        candidates: set[str] | None = None
        if self._projection is not None:
            try:
                candidates = {
                    str(row["entity_id"]) for row in self._projection.query("issue")
                }
            except (ProjectionError, DocumentError):
                candidates = None
        envelopes = self._repository.scan("issue")
        if candidates is not None:
            envelopes = [item for item in envelopes if item.identity in candidates]
        return tuple(_record(item) for item in envelopes)

    def load_issue_record(self, issue_id: EntityId) -> IssueQueryRecord | None:
        envelope = self._repository.load("issue", issue_id)
        return _record(envelope) if envelope else None

    def next_milestone_id(self) -> EntityId | None:
        milestones = (item.aggregate for item in self._repository.scan("milestone"))
        eligible = [
            item
            for item in milestones
            if isinstance(item, Milestone)
            and item.retention is RetentionState.VISIBLE
            and item.status is MilestoneStatus.OPEN
            and item.due_at is not None
        ]
        eligible.sort(key=lambda item: (item.due_at, str(item.id)))
        return eligible[0].id if eligible else None
