"""Phase 6 contracts for target issue query use cases."""

from datetime import UTC, datetime, timedelta

import pytest

from roadmap.application.contracts import (
    IssueListQuery,
    IssueQueryRecord,
    IssueScope,
)
from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.use_cases import IssueQueries
from roadmap.domain.aggregates import Issue
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueStatus,
    Priority,
    RetentionState,
    Timestamp,
    Title,
)

NOW = Timestamp(datetime(2026, 8, 17, 12, tzinfo=UTC))


def _record(identity: str, title: str, **updates) -> IssueQueryRecord:
    values = {
        "id": EntityId(identity),
        "created": NOW,
        "updated": NOW,
        "title": Title(title),
    }
    values.update(updates)
    return IssueQueryRecord(Issue(**values))


class Records:
    def __init__(self, *records: IssueQueryRecord):
        self.records = records
        self.next_id: EntityId | None = EntityId("next")

    def list_issue_records(self):
        return self.records

    def load_issue_record(self, issue_id):
        return next((r for r in self.records if r.issue.id == issue_id), None)

    def next_milestone_id(self):
        return self.next_id


class Identity:
    def current_identity(self):
        return "me"


class Clock:
    def now(self):
        return NOW


def _queries(*records: IssueQueryRecord) -> IssueQueries:
    return IssueQueries(Records(*records), Identity(), Clock())


def test_scope_is_explicit_and_default_excludes_archived() -> None:
    visible = _record("b", "Visible")
    closed = _record("c", "Closed", status=IssueStatus.CLOSED)
    archived = _record("a", "Archived", retention=RetentionState.ARCHIVED)
    queries = _queries(visible, closed, archived)

    assert [r.issue.id for r in queries.list(IssueListQuery()).records] == ["b", "c"]
    assert [
        r.issue.id
        for r in queries.list(IssueListQuery(scope=IssueScope.CLOSED)).records
    ] == ["c"]
    assert [
        r.issue.id
        for r in queries.list(IssueListQuery(scope=IssueScope.ARCHIVED)).records
    ] == ["a"]
    assert len(queries.list(IssueListQuery(scope=IssueScope.ALL)).records) == 3


def test_filters_search_unicode_overdue_and_order_deterministically() -> None:
    matching = _record(
        "z",
        "Café repair",
        priority=Priority.HIGH,
        assignee="me",
        due_at=Timestamp(NOW.value - timedelta(days=1)),
        content="Fix Unicode ☕",
    )
    other = _record("a", "Other")
    result = _queries(matching, other).list(
        IssueListQuery(
            current_assignee=True,
            priority="high",
            overdue=True,
            search="CAFÉ",
        )
    )

    assert result.records == (matching,)
    assert "matching 'CAFÉ'" in result.description


def test_backlog_milestone_and_next_milestone_filters() -> None:
    backlog = _record("backlog", "Backlog")
    planned = _record(
        "planned",
        "Planned",
        relations=IssueRelations(milestone_id=EntityId("next")),
    )
    queries = _queries(planned, backlog)

    assert queries.list(IssueListQuery(backlog=True)).records == (backlog,)
    assert queries.list(IssueListQuery(next_milestone=True)).records == (planned,)


def test_missing_next_milestone_is_distinct_from_empty_result() -> None:
    records = Records()
    records.next_id = None
    result = IssueQueries(records, Identity(), Clock()).list(
        IssueListQuery(next_milestone=True)
    )

    assert result.next_milestone_missing
    assert result.records == ()


@pytest.mark.parametrize(
    "query,message",
    [
        (
            IssueListQuery(assignee="one", current_assignee=True),
            "Cannot combine --assignee",
        ),
        (
            IssueListQuery(backlog=True, milestone=EntityId("milestone")),
            "Cannot combine --backlog",
        ),
    ],
)
def test_conflicting_filters_have_stable_application_failures(query, message) -> None:
    with pytest.raises(ApplicationFailure, match=message) as captured:
        _queries().list(query)

    assert captured.value.category is FailureCategory.INVALID_REQUEST


def test_lookup_uses_complete_identity_and_not_found_is_typed() -> None:
    record = _record("complete-id", "Found")
    queries = _queries(record)

    assert queries.view(EntityId("complete-id")) is record
    with pytest.raises(ApplicationFailure) as captured:
        queries.view(EntityId("missing"))
    assert captured.value.category is FailureCategory.NOT_FOUND
