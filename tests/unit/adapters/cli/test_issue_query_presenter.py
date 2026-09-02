"""Unit tests for IssueQueryPresenter's Rich rendering of issue details.

Builds real Issue/IssueQueryRecord domain objects and captures the real
Rich console output (plain/no-color mode is auto-detected under pytest),
asserting on concrete rendered substrings rather than mocking the console.
A fresh Console is constructed inside each test body (not via a fixture)
so it binds to the sys.stdout object capsys has already redirected.
"""

from datetime import UTC, datetime
from typing import Any

from roadmap.adapters.inbound.cli.console import get_console
from roadmap.adapters.inbound.cli.issues.query_presenter import IssueQueryPresenter
from roadmap.application.contracts import IssueCommentView, IssueQueryRecord
from roadmap.domain.aggregates import Issue
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueStatus,
    IssueType,
    Priority,
    Timestamp,
    Title,
)

_NOW = Timestamp(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
_PRESENTER = IssueQueryPresenter()


def _issue(**overrides) -> Issue:
    defaults: dict[str, Any] = {
        "id": EntityId("issue-1"),
        "created": _NOW,
        "updated": _NOW,
        "title": Title("Fix the parser"),
        "status": IssueStatus.IN_PROGRESS,
        "priority": Priority.HIGH,
        "issue_type": IssueType.BUG,
    }
    defaults.update(overrides)
    return Issue(**defaults)


def _record(issue: Issue, **overrides) -> IssueQueryRecord:
    defaults: dict[str, Any] = {"issue": issue}
    defaults.update(overrides)
    return IssueQueryRecord(**defaults)


def _out(capsys) -> str:
    return capsys.readouterr().out


class TestRenderHeader:
    def test_includes_id_title_status_priority_and_type(self, capsys) -> None:
        _PRESENTER._render_header(get_console(), _issue())
        text = _out(capsys)
        assert "issue-1" in text
        assert "Fix the parser" in text
        assert "IN-PROGRESS" in text
        assert "HIGH" in text
        assert "Bug" in text


class TestRenderMetadata:
    def test_unassigned_issue_shows_unassigned_placeholder(self, capsys) -> None:
        record = _record(_issue(assignee=None))
        _PRESENTER._render_metadata(get_console(), record)
        assert "Unassigned" in _out(capsys)

    def test_assignee_name_is_shown_when_present(self, capsys) -> None:
        record = _record(_issue(assignee="alice"))
        _PRESENTER._render_metadata(get_console(), record)
        assert "alice" in _out(capsys)

    def test_milestone_name_preferred_over_milestone_id(self, capsys) -> None:
        issue = _issue(relations=IssueRelations(milestone_id=EntityId("milestone-1")))
        record = _record(issue, milestone_name="Beta Launch")
        _PRESENTER._render_metadata(get_console(), record)
        text = _out(capsys)
        assert "Beta Launch" in text
        assert "milestone-1" not in text

    def test_milestone_id_shown_when_name_missing(self, capsys) -> None:
        issue = _issue(relations=IssueRelations(milestone_id=EntityId("milestone-1")))
        record = _record(issue, milestone_name=None)
        _PRESENTER._render_metadata(get_console(), record)
        assert "milestone-1" in _out(capsys)

    def test_labels_row_only_rendered_when_labels_present(self, capsys) -> None:
        record = _record(_issue(labels=("urgent", "backend")))
        _PRESENTER._render_metadata(get_console(), record)
        text = _out(capsys)
        assert "urgent" in text
        assert "backend" in text

    def test_no_labels_row_when_labels_empty(self, capsys) -> None:
        record = _record(_issue(labels=()))
        _PRESENTER._render_metadata(get_console(), record)
        assert "Labels" not in _out(capsys)


class TestRenderTimeline:
    def test_not_estimated_placeholder_when_hours_missing(self, capsys) -> None:
        record = _record(_issue(estimated_hours=None))
        _PRESENTER._render_timeline(get_console(), record)
        assert "Not estimated" in _out(capsys)

    def test_estimated_hours_are_formatted_with_one_decimal(self, capsys) -> None:
        record = _record(_issue(estimated_hours=3.0))
        _PRESENTER._render_timeline(get_console(), record)
        assert "3.0h" in _out(capsys)

    def test_completed_row_hidden_without_actual_end_at(self, capsys) -> None:
        record = _record(_issue(), actual_end_at=None)
        _PRESENTER._render_timeline(get_console(), record)
        assert "Completed" not in _out(capsys)

    def test_completed_row_shown_with_actual_end_at(self, capsys) -> None:
        record = _record(_issue(), actual_end_at=_NOW)
        _PRESENTER._render_timeline(get_console(), record)
        assert "Completed" in _out(capsys)

    def test_due_date_hidden_when_absent(self, capsys) -> None:
        record = _record(_issue(due_at=None))
        _PRESENTER._render_timeline(get_console(), record)
        assert "Due Date" not in _out(capsys)

    def test_due_date_shown_when_present(self, capsys) -> None:
        record = _record(_issue(due_at=_NOW))
        _PRESENTER._render_timeline(get_console(), record)
        assert "Due Date" in _out(capsys)


class TestRenderDependencies:
    def test_nothing_rendered_without_dependencies_or_blocks(self, capsys) -> None:
        _PRESENTER._render_dependencies(get_console(), _issue())
        assert _out(capsys) == ""

    def test_depends_on_rendered_when_present(self, capsys) -> None:
        issue = _issue(relations=IssueRelations(depends_on=(EntityId("issue-2"),)))
        _PRESENTER._render_dependencies(get_console(), issue)
        text = _out(capsys)
        assert "Depends on" in text
        assert "issue-2" in text

    def test_blocks_rendered_when_present(self, capsys) -> None:
        issue = _issue(relations=IssueRelations(blocks=(EntityId("issue-3"),)))
        _PRESENTER._render_dependencies(get_console(), issue)
        text = _out(capsys)
        assert "Blocks" in text
        assert "issue-3" in text


class TestRenderDescription:
    def test_placeholder_when_no_content(self, capsys) -> None:
        _PRESENTER._render_description(get_console(), _issue(content=""))
        assert "No description available" in _out(capsys)

    def test_content_rendered_as_markdown(self, capsys) -> None:
        _PRESENTER._render_description(
            get_console(), _issue(content="Some **details**")
        )
        assert "details" in _out(capsys)


class TestRenderComments:
    def test_nothing_rendered_without_comments(self, capsys) -> None:
        record = _record(_issue(), comments=())
        _PRESENTER._render_comments(get_console(), record)
        assert _out(capsys) == ""

    def test_comments_rendered_with_author_and_body(self, capsys) -> None:
        comment = IssueCommentView(
            id=1, author="bob", body="Looks good", created_at=_NOW, updated_at=_NOW
        )
        record = _record(_issue(), comments=(comment,))
        _PRESENTER._render_comments(get_console(), record)
        text = _out(capsys)
        assert "bob" in text
        assert "Looks good" in text
        assert "Comments (1)" in text


class TestRenderFullRecord:
    def test_render_invokes_all_sections_without_raising(self, capsys) -> None:
        issue = _issue(
            assignee="alice",
            labels=("urgent",),
            content="Investigate the root cause",
            due_at=_NOW,
            relations=IssueRelations(depends_on=(EntityId("issue-2"),)),
        )
        comment = IssueCommentView(
            id=1, author="bob", body="Any update?", created_at=_NOW, updated_at=_NOW
        )
        record = _record(issue, comments=(comment,), milestone_name="Beta Launch")

        _PRESENTER.render(record)

        text = _out(capsys)
        assert "Fix the parser" in text
        assert "alice" in text
        assert "Beta Launch" in text
        assert "urgent" in text
        assert "Investigate the root cause" in text
        assert "issue-2" in text
        assert "bob" in text
