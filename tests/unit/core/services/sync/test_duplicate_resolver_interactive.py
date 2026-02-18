"""Additional DuplicateResolver tests for interactive and formatting branches."""

from __future__ import annotations

import builtins
import sys
import types
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from roadmap.common.constants import Priority, Status
from roadmap.common.result import Err, Ok
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.issue.issue_service import IssueService
from roadmap.core.services.sync.duplicate_detector import (
    DuplicateMatch,
    MatchType,
    RecommendedAction,
)
from roadmap.core.services.sync.duplicate_resolver import DuplicateResolver


def _issue_service_mock() -> MagicMock:
    return MagicMock(spec=IssueService)


@pytest.fixture
def local_issue() -> Issue:
    return Issue(
        id="local-1",
        title="Fix auth bug",
        status=Status.IN_PROGRESS,
        priority=Priority.HIGH,
        assignee="alice",
        labels=["bug"],
        created=datetime(2024, 1, 1, tzinfo=UTC),
        updated=datetime(2024, 1, 2, tzinfo=UTC),
    )


@pytest.fixture
def remote_issue() -> SyncIssue:
    return SyncIssue(
        id="remote-1",
        title="Fix auth bug",
        status="in-progress",
        assignee="bob",
        labels=["bug", "oauth"],
        backend_name="github",
        backend_id=123,
    )


@pytest.fixture
def match(local_issue: Issue, remote_issue: SyncIssue) -> DuplicateMatch:
    return DuplicateMatch(
        local_issue=local_issue,
        remote_issue=remote_issue,
        match_type=MatchType.TITLE_EXACT,
        confidence=0.97,
        recommended_action=RecommendedAction.AUTO_MERGE,
        similarity_details={"title_similarity": 1.0, "source": "exact"},
    )


def _install_fake_rich(
    monkeypatch: pytest.MonkeyPatch, responses: list[str]
) -> list[str]:
    printed: list[str] = []

    class _Console:
        def print(self, obj):
            printed.append(str(obj))

    class _Prompt:
        @staticmethod
        def ask(_message, choices=None, default=None):
            if responses:
                return responses.pop(0)
            return default or "skip"

    console_mod = types.ModuleType("rich.console")
    cast(Any, console_mod).Console = _Console
    prompt_mod = types.ModuleType("rich.prompt")
    cast(Any, prompt_mod).Prompt = _Prompt

    monkeypatch.setitem(sys.modules, "rich.console", console_mod)
    monkeypatch.setitem(sys.modules, "rich.prompt", prompt_mod)
    return printed


def test_resolve_interactive_skips_when_rich_unavailable(match: DuplicateMatch) -> None:
    resolver = DuplicateResolver(issue_service=_issue_service_mock())

    original_import = builtins.__import__

    def _raising_import(name, *args, **kwargs):
        if name.startswith("rich"):
            raise ImportError("rich missing")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = _raising_import
    try:
        actions = resolver.resolve_interactive([match])
    finally:
        builtins.__import__ = original_import

    assert len(actions) == 1
    assert actions[0].action_type == "skip"


def test_resolve_interactive_merge_success(
    monkeypatch: pytest.MonkeyPatch, match: DuplicateMatch
) -> None:
    canonical = Issue(id="local-1", title="Merged", status=Status.IN_PROGRESS)
    issue_service = _issue_service_mock()
    issue_service.merge_issues.return_value = Ok(canonical)
    resolver = DuplicateResolver(issue_service=issue_service)

    _install_fake_rich(monkeypatch, ["merge"])

    actions = resolver.resolve_interactive([match])

    assert len(actions) == 1
    assert actions[0].action_type == "merge"
    assert actions[0].canonical_issue is canonical


def test_resolve_interactive_merge_failure_returns_skip_with_error(
    monkeypatch: pytest.MonkeyPatch, match: DuplicateMatch
) -> None:
    issue_service = _issue_service_mock()
    issue_service.merge_issues.return_value = Err("cannot merge")
    resolver = DuplicateResolver(issue_service=issue_service)

    _install_fake_rich(monkeypatch, ["merge"])

    actions = resolver.resolve_interactive([match])

    assert len(actions) == 1
    assert actions[0].action_type == "skip"
    assert actions[0].error == "Merge failed: cannot merge"


def test_resolve_interactive_keep_and_skip(
    monkeypatch: pytest.MonkeyPatch, local_issue: Issue, remote_issue: SyncIssue
) -> None:
    second = DuplicateMatch(
        local_issue=Issue(id="local-2", title="Other", status=Status.TODO),
        remote_issue=SyncIssue(
            id="remote-2",
            title="Other",
            status="todo",
            backend_name="github",
            backend_id=22,
        ),
        match_type=MatchType.TITLE_EXACT,
        confidence=0.95,
        recommended_action=RecommendedAction.MANUAL_REVIEW,
    )
    first = DuplicateMatch(
        local_issue=local_issue,
        remote_issue=remote_issue,
        match_type=MatchType.TITLE_EXACT,
        confidence=0.96,
        recommended_action=RecommendedAction.MANUAL_REVIEW,
    )

    resolver = DuplicateResolver(issue_service=_issue_service_mock())
    _install_fake_rich(monkeypatch, ["keep", "skip"])

    actions = resolver.resolve_interactive([first, second])

    assert [a.action_type for a in actions] == ["keep", "skip"]


def test_format_match_details_returns_none_without_rich(match: DuplicateMatch) -> None:
    resolver = DuplicateResolver(issue_service=_issue_service_mock())

    original_import = builtins.__import__

    def _raising_import(name, *args, **kwargs):
        if name.startswith("rich"):
            raise ImportError("rich missing")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = _raising_import
    try:
        panel = resolver._format_match_details(match)
    finally:
        builtins.__import__ = original_import

    assert panel is None


def test_format_match_details_returns_panel(match: DuplicateMatch) -> None:
    resolver = DuplicateResolver(issue_service=_issue_service_mock())

    panel = resolver._format_match_details(match)

    assert panel is not None
    assert "Potential Duplicate" in str(panel.title)
