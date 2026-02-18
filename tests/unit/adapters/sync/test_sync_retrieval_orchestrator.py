"""Behavior-focused tests for SyncRetrievalOrchestrator."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

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
