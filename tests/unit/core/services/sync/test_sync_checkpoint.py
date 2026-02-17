"""Behavioral tests for sync checkpoint recovery helpers."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

from roadmap.core.services.sync.sync_checkpoint import (
    SyncCheckpoint,
    SyncCheckpointManager,
)


@dataclass
class _IssueSnapshot:
    id: str
    title: str
    updated: datetime


def _manager(core: Mock | None = None) -> SyncCheckpointManager:
    return SyncCheckpointManager(core or Mock())


def test_create_checkpoint_tracks_modified_issue_ids(monkeypatch):
    manager = _manager(Mock(db=Mock()))
    monkeypatch.setattr(manager, "_save_checkpoint", Mock())
    monkeypatch.setattr(
        manager,
        "_serialize_issue",
        lambda issue: {"id": issue.id, "title": issue.title},
    )
    monkeypatch.setattr(manager, "_is_modified", lambda issue: issue.id == "A")

    issues = [
        SimpleNamespace(id="A", title="one"),
        SimpleNamespace(id="B", title="two"),
    ]
    checkpoint = manager.create_checkpoint("push", cast(Any, issues))

    assert checkpoint.phase == "push"
    assert checkpoint.modified_issues == ["A"]
    assert set(checkpoint.baseline_state.keys()) == {"A", "B"}


def test_serialize_issue_converts_datetime_to_iso():
    manager = _manager()
    ts = datetime(2025, 1, 1, tzinfo=UTC)
    snapshot = _IssueSnapshot(id="I1", title="Issue", updated=ts)

    data = manager._serialize_issue(cast(Any, snapshot))

    assert data["updated"] == ts.isoformat()


def test_is_modified_detects_private_flags():
    manager = _manager()
    issue = SimpleNamespace(_modified=True, _local_changes=None)
    assert manager._is_modified(cast(Any, issue)) is True


def test_get_latest_checkpoint_returns_none_on_db_error():
    state_manager = Mock()
    state_manager.get_sync_checkpoint.side_effect = RuntimeError("db unavailable")
    manager = _manager(Mock(db=state_manager))

    checkpoint = manager.get_latest_checkpoint()

    assert checkpoint is None


def test_can_resume_recent_fetch_checkpoint():
    manager = _manager()
    checkpoint = SyncCheckpoint(
        checkpoint_id="c1",
        timestamp=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        phase="fetch",
        baseline_state={},
        modified_issues=[],
        github_operations=[],
        metadata={},
    )
    manager.get_latest_checkpoint = Mock(return_value=checkpoint)

    can_resume, returned = manager.can_resume()

    assert can_resume is True
    assert returned == checkpoint


def test_can_resume_rejects_old_or_non_resumable():
    manager = _manager()
    old_checkpoint = SyncCheckpoint(
        checkpoint_id="c2",
        timestamp=(datetime.now(UTC) - timedelta(hours=2)).isoformat(),
        phase="push",
        baseline_state={},
        modified_issues=[],
        github_operations=[],
        metadata={},
    )
    manager.get_latest_checkpoint = Mock(return_value=old_checkpoint)
    assert manager.can_resume()[0] is False

    new_complete = SyncCheckpoint(
        checkpoint_id="c3",
        timestamp=datetime.now(UTC).isoformat(),
        phase="complete",
        baseline_state={},
        modified_issues=[],
        github_operations=[],
        metadata={},
    )
    manager.get_latest_checkpoint = Mock(return_value=new_complete)
    assert manager.can_resume()[0] is False


def test_rollback_to_checkpoint_restores_and_clears_flags(monkeypatch):
    issues = Mock()
    issue_obj = SimpleNamespace(
        id="A",
        title="Old",
        status="todo",
        assignee="sam",
        _modified=True,
        _local_changes={"status": "in_progress"},
    )
    issues.get.return_value = issue_obj
    core = Mock(issues=issues, db=Mock())
    manager = _manager(core)
    monkeypatch.setattr(manager, "clear_checkpoint", Mock())

    checkpoint = SyncCheckpoint(
        checkpoint_id="cp",
        timestamp=datetime.now(UTC).isoformat(),
        phase="push",
        baseline_state={
            "A": {"title": "Restored", "status": "closed", "assignee": "sam"}
        },
        modified_issues=["A"],
        github_operations=[],
        metadata={},
    )

    success = manager.rollback_to_checkpoint(checkpoint)

    assert success is True
    assert issue_obj.title == "Restored"
    assert issue_obj.status == "closed"
    assert issue_obj._modified is False
    assert issue_obj._local_changes is None
    issues.update.assert_called_once()


def test_clear_checkpoint_removes_latest_when_matching():
    state_manager = Mock()
    state_manager.get_sync_checkpoint.return_value = {"checkpoint_id": "abc"}
    manager = _manager(Mock(db=state_manager))

    manager.clear_checkpoint("abc")

    state_manager.delete_sync_checkpoint.assert_any_call("sync_checkpoint_abc")
    state_manager.delete_sync_checkpoint.assert_any_call("latest_checkpoint")
