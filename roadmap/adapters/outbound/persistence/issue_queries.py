"""Canonical issue query adapter with disposable SQLite candidate selection."""

from __future__ import annotations

from roadmap.application.contracts import IssueCommentView, IssueQueryRecord
from roadmap.domain.aggregates import Issue, Milestone
from roadmap.domain.types import EntityId, MilestoneStatus, RetentionState

from .documents import DocumentEnvelope, DocumentError, DocumentRepository
from .projection import ProjectionError, SQLiteProjection


def _record(envelope: DocumentEnvelope) -> IssueQueryRecord:
    aggregate = envelope.aggregate
    if not isinstance(aggregate, Issue):
        raise DocumentError(f"expected issue document, got {envelope.kind}")
    return IssueQueryRecord(
        issue=aggregate,
        comments=tuple(
            IssueCommentView(
                id=comment.id,
                author=comment.author,
                body=comment.body,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                in_reply_to=comment.in_reply_to,
            )
            for comment in aggregate.comments
        ),
        actual_end_at=aggregate.actual_end_at,
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
