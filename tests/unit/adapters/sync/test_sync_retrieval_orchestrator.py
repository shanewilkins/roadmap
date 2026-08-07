"""Behavior-focused tests for SyncRetrievalOrchestrator."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.sync.sync_retrieval_orchestrator import SyncRetrievalOrchestrator
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.baseline.baseline_selector import BaselineStrategy
from roadmap.core.services.sync.sync_state import IssueBaseState, SyncState


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


def _orchestrator() -> Any:
    orchestrator = object.__new__(SyncRetrievalOrchestrator)
    orchestrator.core = Mock()
    orchestrator.core.db = Mock()
    orchestrator.core.issues = Mock()
    orchestrator.core.roadmap_dir = Path("/tmp/roadmap")
    orchestrator.state_manager = Mock()
    orchestrator.baseline_selector = Mock()
    orchestrator.backend = Mock()
    orchestrator._find_issue_file = Mock(return_value=Path("/tmp/roadmap/issues/A.md"))
    return cast(Any, orchestrator)


def test_has_baseline_true_when_db_contains_baseline():
    orchestrator = _orchestrator()
    orchestrator.core.db.get_sync_baseline.return_value = {"A": {"status": "todo"}}

    assert orchestrator.has_baseline() is True


def test_has_baseline_true_when_legacy_state_has_issues():
    orchestrator = _orchestrator()
    orchestrator.core.db.get_sync_baseline.return_value = {}
    orchestrator.state_manager.load_sync_state.return_value = SyncState(
        base_issues={"A": IssueBaseState(id="A", status="todo")}
    )

    assert orchestrator.has_baseline() is True


def test_has_baseline_true_when_sync_metadata_contains_last_synced(monkeypatch):
    orchestrator = _orchestrator()
    orchestrator.core.db.get_sync_baseline.return_value = {}
    orchestrator.state_manager.load_sync_state.return_value = None
    orchestrator.core.issues.list_all_including_archived.return_value = [
        SimpleNamespace(id="A")
    ]
    monkeypatch.setattr(
        "roadmap.adapters.sync.sync_retrieval_orchestrator.IssueParser.load_sync_metadata",
        lambda _p: {"last_synced": "2026-01-01T00:00:00+00:00"},
    )

    assert orchestrator.has_baseline() is True


def test_ensure_baseline_raises_when_noninteractive_without_strategy():
    orchestrator = _orchestrator()
    orchestrator.has_baseline = Mock(return_value=False)

    with pytest.raises(RuntimeError):
        orchestrator.ensure_baseline(strategy=None, interactive=False)


def test_ensure_baseline_routes_to_local_strategy():
    orchestrator = _orchestrator()
    orchestrator.has_baseline = Mock(return_value=False)
    orchestrator._create_baseline_from_local = Mock(return_value=True)

    ok = orchestrator.ensure_baseline(strategy=BaselineStrategy.LOCAL)

    assert ok is True
    orchestrator._create_baseline_from_local.assert_called_once()


def test_ensure_baseline_defaults_interactive_to_local_fallback():
    orchestrator = _orchestrator()
    orchestrator.has_baseline = Mock(return_value=False)
    orchestrator.baseline_selector.select_baseline.return_value = SimpleNamespace(
        strategy=BaselineStrategy.INTERACTIVE
    )
    orchestrator._create_baseline_from_local = Mock(return_value=True)

    ok = orchestrator.ensure_baseline(strategy=None, interactive=True)

    assert ok is True
    orchestrator._create_baseline_from_local.assert_called_once()


def test_authenticate_for_baseline_handles_result_and_bool_variants():
    orchestrator = _orchestrator()

    orchestrator.backend.authenticate.return_value = _FakeResult(value=True)
    assert orchestrator._authenticate_for_baseline() is True

    orchestrator.backend.authenticate.return_value = _FakeResult(error="bad token")
    assert orchestrator._authenticate_for_baseline() is False

    orchestrator.backend.authenticate.return_value = True
    assert orchestrator._authenticate_for_baseline() is True

    orchestrator.backend.authenticate.return_value = False
    assert orchestrator._authenticate_for_baseline() is False


def test_fetch_remote_issues_for_baseline_handles_result_dict_and_invalid():
    orchestrator = _orchestrator()

    data = {"A": SyncIssue(id="A", title="Issue", status="todo")}
    orchestrator.backend.get_issues.return_value = _FakeResult(value=data)
    assert orchestrator._fetch_remote_issues_for_baseline() == data

    orchestrator.backend.get_issues.return_value = data
    assert orchestrator._fetch_remote_issues_for_baseline() == data

    orchestrator.backend.get_issues.return_value = _FakeResult(error="no access")
    assert orchestrator._fetch_remote_issues_for_baseline() is None

    orchestrator.backend.get_issues.return_value = "unexpected"
    assert orchestrator._fetch_remote_issues_for_baseline() is None


def test_build_baseline_from_remote_issues_maps_fields():
    orchestrator = _orchestrator()
    remote = {
        "A": SyncIssue(
            id="A",
            title="Alpha",
            status="in_progress",
            assignee="dev",
            labels=["sync"],
        )
    }

    baseline = orchestrator._build_baseline_from_remote_issues(remote)

    assert "A" in baseline.base_issues
    state = baseline.base_issues["A"]
    assert state.status == "in_progress"
    assert state.assignee == "dev"
    assert state.labels == ["sync"]


def test_ensure_baseline_routes_to_remote_strategy():
    orchestrator = _orchestrator()
    orchestrator.has_baseline = Mock(return_value=False)
    orchestrator._create_baseline_from_remote = Mock(return_value=True)

    ok = orchestrator.ensure_baseline(strategy=BaselineStrategy.REMOTE)

    assert ok is True
    orchestrator._create_baseline_from_remote.assert_called_once()


def test_create_baseline_from_remote_returns_false_on_auth_failure():
    orchestrator = _orchestrator()
    orchestrator._authenticate_for_baseline = Mock(return_value=False)

    assert orchestrator._create_baseline_from_remote() is False


def test_create_baseline_from_remote_saves_baseline_dict():
    orchestrator = _orchestrator()
    orchestrator._authenticate_for_baseline = Mock(return_value=True)
    orchestrator._fetch_remote_issues_for_baseline = Mock(
        return_value={
            "A": SyncIssue(id="A", title="Remote", status="todo", labels=["x"])
        }
    )

    ok = orchestrator._create_baseline_from_remote()

    assert ok is True
    orchestrator.core.db.save_sync_baseline.assert_called_once()
    saved = orchestrator.core.db.save_sync_baseline.call_args.args[0]
    assert saved["A"]["status"] == "todo"
    assert saved["A"]["labels"] == ["x"]


def test_find_issue_file_searches_backlog_root_and_milestone(tmp_path):
    orchestrator = object.__new__(SyncRetrievalOrchestrator)
    orchestrator.core = Mock()
    orchestrator.core.roadmap_dir = tmp_path / ".roadmap"
    issues_dir = orchestrator.issues_dir
    (issues_dir / "backlog").mkdir(parents=True)
    (issues_dir / "m1").mkdir(parents=True)

    backlog_file = issues_dir / "backlog" / "ABC-1.md"
    backlog_file.write_text("x")

    found = orchestrator._find_issue_file("ABC")
    assert found == backlog_file


def test_get_baseline_state_returns_db_converted_syncstate():
    orchestrator = _orchestrator()
    orchestrator.core.db.get_sync_baseline.return_value = {
        "I1": {
            "status": "in_progress",
            "assignee": "alice",
            "description": "desc",
            "labels": ["l1"],
        }
    }

    state = orchestrator.get_baseline_state()

    assert state is not None
    assert state.base_issues["I1"].status == "in_progress"
    assert state.base_issues["I1"].assignee == "alice"
    assert state.base_issues["I1"].description == "desc"


def test_sync_all_issues_uses_git_baseline_and_restores_loader():
    orchestrator = _orchestrator()
    orchestrator.get_baseline_state = Mock(
        return_value=SyncState(base_issues={"A": IssueBaseState(id="A", status="todo")})
    )

    original = orchestrator.state_manager.load_sync_state
    with patch(
        "roadmap.adapters.sync.sync_retrieval_orchestrator.SyncMergeOrchestrator.sync_all_issues",
        return_value="ok",
    ) as mock_parent:
        result = orchestrator.sync_all_issues(dry_run=False, push_only=True)

    assert result == "ok"
    mock_parent.assert_called_once_with(
        dry_run=False,
        force_local=False,
        force_remote=False,
        push_only=True,
        pull_only=False,
    )
    assert orchestrator.state_manager.load_sync_state is original
