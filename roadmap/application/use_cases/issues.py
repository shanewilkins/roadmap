"""Read-only issue application use cases."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC

from roadmap.application.contracts import (
    IssueListQuery,
    IssueListResult,
    IssueQueryRecord,
    IssueScope,
)
from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.ports import Clock, CurrentIdentity, ReadIssueRecords
from roadmap.domain.types import EntityId, IssueStatus, RetentionState


class IssueQueries:
    """One target path for retained issue lookup, detail, and list behavior."""

    def __init__(
        self, records: ReadIssueRecords, identity: CurrentIdentity, clock: Clock
    ):
        self._records = records
        self._identity = identity
        self._clock = clock

    def ids(self) -> tuple[EntityId, ...]:
        return tuple(record.issue.id for record in self._records.list_issue_records())

    def list_all(self) -> tuple[IssueQueryRecord, ...]:
        """Return deterministic canonical records for another Application use case."""
        return tuple(
            sorted(
                self._records.list_issue_records(), key=lambda item: str(item.issue.id)
            )
        )

    def view(self, issue_id: EntityId) -> IssueQueryRecord:
        record = self._records.load_issue_record(issue_id)
        if record is None:
            raise ApplicationFailure(
                FailureCategory.NOT_FOUND, f"Issue '{issue_id}' was not found"
            )
        return record

    def list(self, query: IssueListQuery) -> IssueListResult:
        self._validate(query)
        records = [
            record
            for record in self._records.list_issue_records()
            if self._in_scope(record, query.scope)
        ]
        initial_description = (
            "all" if query.scope is IssueScope.VISIBLE else query.scope.value
        )
        records, description, missing = self._select_milestone(
            records, query, initial_description
        )
        if missing:
            return IssueListResult((), "", next_milestone_missing=True)
        records, description = self._select_assignee(records, query, description)
        records, description = self._apply_filters(records, query, description)
        records.sort(key=lambda record: str(record.issue.id))
        return IssueListResult(tuple(records), description)

    def _select_milestone(
        self,
        records: list[IssueQueryRecord],
        query: IssueListQuery,
        description: str,
    ) -> tuple[list[IssueQueryRecord], str, bool]:
        milestone = query.milestone
        if query.next_milestone:
            milestone = self._records.next_milestone_id()
            if milestone is None:
                return [], "", True
            description = f"next milestone ({milestone})"
        elif query.backlog:
            return (
                [r for r in records if r.issue.relations.milestone_id is None],
                "backlog",
                False,
            )
        elif milestone is not None:
            description = f"milestone '{milestone}'"
        if milestone is not None:
            records = [
                r for r in records if r.issue.relations.milestone_id == milestone
            ]
        return records, description, False

    def _select_assignee(
        self,
        records: list[IssueQueryRecord],
        query: IssueListQuery,
        description: str,
    ) -> tuple[list[IssueQueryRecord], str]:
        assignee = query.assignee
        if query.current_assignee:
            assignee = self._identity.current_identity()
            description = "my"
            if assignee is None:
                return [], description
        elif assignee:
            description = f"assigned to {assignee}"
        if assignee:
            records = [r for r in records if r.issue.assignee == assignee]
        return records, description

    def _apply_filters(
        self,
        records: list[IssueQueryRecord],
        query: IssueListQuery,
        description: str,
    ) -> tuple[list[IssueQueryRecord], str]:
        filters: tuple[tuple[bool, Callable[[IssueQueryRecord], bool], str], ...] = (
            (
                query.open_only,
                lambda r: r.issue.status is not IssueStatus.CLOSED,
                "open",
            ),
            (
                query.blocked_only,
                lambda r: r.issue.status is IssueStatus.BLOCKED,
                "blocked",
            ),
            (
                query.status is not None,
                lambda r: r.issue.status.value == query.status,
                query.status or "",
            ),
            (
                query.priority is not None,
                lambda r: r.issue.priority.value == query.priority,
                f"{query.priority} priority",
            ),
            (
                query.issue_type is not None,
                lambda r: r.issue.issue_type.value == query.issue_type,
                query.issue_type or "",
            ),
            (query.overdue, self._overdue, "overdue"),
        )
        for enabled, predicate, label in filters:
            if enabled:
                records = [record for record in records if predicate(record)]
                description = f"{description} {label}".strip()
        if query.search:
            needle = query.search.casefold()
            records = [
                record
                for record in records
                if needle
                in "\n".join(
                    (
                        str(record.issue.title),
                        record.issue.headline,
                        record.issue.content,
                    )
                ).casefold()
            ]
            description = f"{description} matching '{query.search}'"
        return records, description

    @staticmethod
    def _validate(query: IssueListQuery) -> None:
        if query.assignee and query.current_assignee:
            raise ApplicationFailure(
                FailureCategory.INVALID_REQUEST,
                "Cannot combine --assignee and --my-issues filters",
            )
        milestone_filters = (
            query.backlog,
            query.next_milestone,
            query.milestone is not None,
        )
        if sum(milestone_filters) > 1:
            raise ApplicationFailure(
                FailureCategory.INVALID_REQUEST,
                "Cannot combine --backlog, --unassigned, --next-milestone, and --milestone filters",
            )

    @staticmethod
    def _in_scope(record: IssueQueryRecord, scope: IssueScope) -> bool:
        issue = record.issue
        if scope is IssueScope.ALL:
            return issue.retention is not RetentionState.PURGED
        if scope is IssueScope.ARCHIVED:
            return issue.retention is RetentionState.ARCHIVED
        if issue.retention is not RetentionState.VISIBLE:
            return False
        return scope is not IssueScope.CLOSED or issue.status is IssueStatus.CLOSED

    def _overdue(self, record: IssueQueryRecord) -> bool:
        due = record.issue.due_at
        now = self._clock.now().value.astimezone(UTC)
        return bool(due and due.value.astimezone(UTC) < now)
