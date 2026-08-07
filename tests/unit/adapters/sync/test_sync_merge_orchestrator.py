"""Behavior-focused tests for SyncMergeOrchestrator analysis planning."""

from types import SimpleNamespace
from typing import Any, cast

from roadmap.adapters.sync.sync_merge_orchestrator import SyncMergeOrchestrator


class _FakeResult:
    def __init__(self, value=None, error=None):
        self._value = value
        self._error = error

    def is_err(self):
        return self._error is not None

    def unwrap(self):
        return self._value

    def unwrap_err(self):
        return self._error


def _change(
    issue_id: str,
    has_conflict: bool = False,
    local_only: bool = False,
    remote_only: bool = False,
):
    local_state = SimpleNamespace(id=issue_id, status="todo") if local_only else None
    remote_state = {"status": "open", "backend_id": issue_id} if remote_only else {}

    return SimpleNamespace(
        issue_id=issue_id,
        title=f"Issue {issue_id}",
        has_conflict=has_conflict,
        conflict_type="no_change"
        if not (local_only or remote_only or has_conflict)
        else "changed",
        local_state=local_state,
        remote_state=remote_state,
        local_changes={"status": "closed"} if has_conflict else {},
        is_local_only_change=lambda: local_only,
        is_remote_only_change=lambda: remote_only,
    )


def _orchestrator() -> Any:
    orchestrator: Any = object.__new__(SyncMergeOrchestrator)
    orchestrator.backend = SimpleNamespace(authenticate=None, get_issues=None)
    orchestrator.core = SimpleNamespace(
        issues=SimpleNamespace(list_all_including_archived=None)
    )
    orchestrator.state_comparator = SimpleNamespace(analyze_three_way=None)
    orchestrator._load_baseline_state = lambda: None
    return cast(Any, orchestrator)


def test_analyze_all_issues_returns_error_on_auth_failure():
    orchestrator = _orchestrator()
    orchestrator.backend.authenticate = lambda: _FakeResult(error="auth failed")

    plan, report = orchestrator.analyze_all_issues()

    assert plan.actions == []
    assert report.error == "auth failed"


def test_analyze_all_issues_returns_error_on_get_issues_failure():
    orchestrator = _orchestrator()
    orchestrator.backend.authenticate = lambda: _FakeResult(value=True)
    orchestrator.backend.get_issues = lambda: _FakeResult(error="backend down")

    plan, report = orchestrator.analyze_all_issues()

    assert plan.actions == []
    assert report.error == "backend down"


def test_analyze_all_issues_handles_local_fetch_exception():
    orchestrator = _orchestrator()
    orchestrator.backend.authenticate = lambda: _FakeResult(value=True)
    orchestrator.backend.get_issues = lambda: _FakeResult(value={})

    def _boom():
        raise RuntimeError("disk unavailable")

    orchestrator.core.issues.list_all_including_archived = _boom

    plan, report = orchestrator.analyze_all_issues()

    assert plan.actions == []
    assert "Failed to fetch local issues" in (report.error or "")


def test_analyze_all_issues_builds_push_pull_conflict_actions():
    orchestrator = _orchestrator()
    orchestrator.backend.authenticate = lambda: _FakeResult(value=True)
    orchestrator.backend.get_issues = lambda: _FakeResult(
        value={"R1": {"status": "open"}}
    )
    orchestrator.core.issues.list_all_including_archived = lambda: [
        SimpleNamespace(id="L1")
    ]
    orchestrator.state_comparator.analyze_three_way = lambda *_args, **_kwargs: [
        _change("L1", local_only=True),
        _change("R1", remote_only=True),
        _change("C1", has_conflict=True),
        _change("N1"),
    ]

    plan, report = orchestrator.analyze_all_issues()

    action_types = [action.action_type for action in plan.actions]
    assert action_types.count("push") == 1
    assert action_types.count("pull") == 1
    assert action_types.count("resolve_conflict") == 1
    assert report.total_issues == 1
    assert report.issues_needs_push == 1
    assert report.issues_needs_pull == 1
    assert report.conflicts_detected == 1
    assert report.issues_up_to_date == 1


def test_analyze_all_issues_respects_push_only_and_pull_only():
    orchestrator = _orchestrator()
    orchestrator.backend.authenticate = lambda: _FakeResult(value=True)
    orchestrator.backend.get_issues = lambda: _FakeResult(
        value={"R1": {"status": "open"}}
    )
    orchestrator.core.issues.list_all_including_archived = lambda: [
        SimpleNamespace(id="L1")
    ]
    orchestrator.state_comparator.analyze_three_way = lambda *_args, **_kwargs: [
        _change("L1", local_only=True),
        _change("R1", remote_only=True),
    ]

    push_plan, _ = orchestrator.analyze_all_issues(push_only=True)
    pull_plan, _ = orchestrator.analyze_all_issues(pull_only=True)

    push_types = [action.action_type for action in push_plan.actions]
    pull_types = [action.action_type for action in pull_plan.actions]
    assert "pull" not in push_types
    assert "push" in push_types
    assert "push" not in pull_types
    assert "pull" in pull_types
