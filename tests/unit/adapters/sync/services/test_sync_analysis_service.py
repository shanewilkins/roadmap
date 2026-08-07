"""Tests for SyncAnalysisService."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from roadmap.adapters.sync.services.sync_analysis_service import SyncAnalysisService
from roadmap.core.services.sync.sync_state import IssueBaseState, SyncState


def test_load_baseline_safe_prefers_state_manager():
    """Should return DB baseline from state manager when available."""
    state_manager = MagicMock()
    baseline = SyncState(
        last_sync_time=datetime.now(UTC),
        base_issues={"a": IssueBaseState(id="a", status="todo")},
    )
    state_manager.load_sync_state_from_db.return_value = baseline
    service = SyncAnalysisService(MagicMock(), state_manager)

    result = service.load_baseline_safe()

    assert result is baseline


def test_load_baseline_safe_falls_back_to_core_db():
    """When state manager has no baseline, core DB baseline should be converted."""
    state_manager = MagicMock()
    state_manager.load_sync_state_from_db.return_value = None
    core = MagicMock()
    core.db.get_sync_baseline.return_value = {
        "1": {
            "status": "in_progress",
            "title": "Issue",
            "assignee": "alice",
            "headline": "H",
            "content": "Body",
            "labels": ["x"],
        }
    }
    service = SyncAnalysisService(MagicMock(), state_manager, core=core)

    result = service.load_baseline_safe()

    assert result is not None
    assert result.base_issues["1"].status == "in_progress"
    assert result.base_issues["1"].assignee == "alice"
    assert result.base_issues["1"].labels == ["x"]


def test_load_baseline_safe_swallows_exception_and_returns_none():
    """Exceptions from baseline loading should be converted to None."""
    state_manager = MagicMock()
    state_manager.load_sync_state_from_db.side_effect = RuntimeError("boom")
    service = SyncAnalysisService(MagicMock(), state_manager)

    result = service.load_baseline_safe()

    assert result is None


def test_should_reclassify_as_push_requires_empty_remote_and_nonempty_local():
    """Only labels/assignee empty-remote changes with local values should reclassify."""
    service = SyncAnalysisService(MagicMock(), MagicMock())
    local_issue = SimpleNamespace(labels=["bug"], assignee="dev", content="")
    change = SimpleNamespace(
        remote_changes={"labels": {"to": []}, "assignee": {"to": None}},
        local_state=local_issue,
    )

    assert service._should_reclassify_as_push(change) is True

    change.remote_changes["labels"] = {"to": ["existing"]}
    assert service._should_reclassify_as_push(change) is False


def test_build_pull_ids_prefers_remote_backend_ids_and_fallbacks():
    """Pull IDs should come from backend IDs, then numeric/synthetic fallback."""
    service = SyncAnalysisService(MagicMock(), MagicMock())
    changes = [
        SimpleNamespace(issue_id="loc-1"),
        SimpleNamespace(issue_id="123"),
        SimpleNamespace(issue_id="_remote_88"),
        SimpleNamespace(issue_id="abc"),
    ]
    normalized_remote = {
        "loc-1": {"backend_id": 42},
    }

    pulls = service._build_pull_ids(changes, normalized_remote)

    assert "42" in pulls
    assert "123" in pulls
    assert "_remote_88" in pulls
    assert "abc" not in pulls


def test_analyze_and_classify_reclassifies_and_normalizes_keys():
    """Analyze path should reclassify eligible remote-only changes and derive pulls."""
    local_issue = SimpleNamespace(id="L1", labels=["x"], assignee="alice", content="")

    local_only = SimpleNamespace(
        issue_id="L0",
        local_state=SimpleNamespace(id="L0"),
        remote_state=None,
        conflict_type="local_only",
        has_conflict=False,
        remote_changes={},
        is_local_only_change=lambda: True,
        is_remote_only_change=lambda: False,
    )
    remote_only_reclass = SimpleNamespace(
        issue_id="L1",
        local_state=local_issue,
        remote_state={"backend_id": 101, "status": "todo"},
        conflict_type="remote_only",
        has_conflict=False,
        remote_changes={"labels": {"to": []}},
        is_local_only_change=lambda: False,
        is_remote_only_change=lambda: True,
    )
    remote_only_pull = SimpleNamespace(
        issue_id="R2",
        local_state=None,
        remote_state={"backend_id": 202, "status": "todo"},
        conflict_type="remote_only",
        has_conflict=False,
        remote_changes={},
        is_local_only_change=lambda: False,
        is_remote_only_change=lambda: True,
    )
    no_change = SimpleNamespace(
        issue_id="N1",
        local_state=None,
        remote_state=None,
        conflict_type="no_change",
        has_conflict=False,
        remote_changes={},
        is_local_only_change=lambda: False,
        is_remote_only_change=lambda: False,
    )

    comparator = MagicMock()
    comparator.backend = object()
    comparator.analyze_three_way.return_value = [
        local_only,
        remote_only_reclass,
        remote_only_pull,
        no_change,
    ]

    service = SyncAnalysisService(comparator, MagicMock())

    with patch(
        "roadmap.adapters.sync.services.sync_analysis_service.normalize_remote_keys",
        return_value=(
            {},
            {
                "R2": {"backend_id": 202},
                "L1": {"backend_id": 101},
            },
        ),
    ):
        (
            _changes,
            conflicts,
            local_only_changes,
            remote_only_changes,
            _no_changes,
            updates,
            pulls,
            up_to_date,
        ) = service.analyze_and_classify(
            {"L1": local_issue},
            {"R2": {"backend_id": 202}},
            SyncState(base_issues={}),
        )

    assert conflicts == []
    assert len(local_only_changes) == 2
    assert len(remote_only_changes) == 1
    assert len(updates) == 2
    assert pulls == ["202"]
    assert up_to_date == ["N1"]
