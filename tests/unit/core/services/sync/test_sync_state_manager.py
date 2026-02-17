"""Behavioral tests for SyncStateManager DB and migration paths."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from roadmap.common.constants import Status
from roadmap.core.domain.issue import Issue
from roadmap.core.services.sync.sync_state import IssueBaseState, SyncState
from roadmap.core.services.sync.sync_state_manager import SyncStateManager


class _DbManager:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _get_connection(self):
        return self._conn


def _build_manager(tmp_path: Path) -> tuple[SyncStateManager, sqlite3.Connection]:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE sync_metadata (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)"
    )
    conn.execute(
        """
        CREATE TABLE sync_base_state (
            issue_id TEXT PRIMARY KEY,
            status TEXT,
            assignee TEXT,
            title TEXT,
            description TEXT,
            labels TEXT,
            synced_at TEXT
        )
        """
    )
    manager = SyncStateManager(tmp_path, db_manager=_DbManager(conn))
    return manager, conn


def test_save_sync_state_to_db_round_trip(tmp_path: Path):
    manager, _conn = _build_manager(tmp_path)
    state = SyncState(
        last_sync_time=datetime.now(UTC),
        base_issues={
            "A": IssueBaseState(
                id="A",
                status="todo",
                assignee="dev",
                title="Alpha",
                description="desc",
                labels=["backend"],
            )
        },
    )

    assert manager.save_sync_state_to_db(state) is True

    loaded = manager.load_sync_state_from_db()
    assert loaded is not None
    assert "A" in loaded.base_issues
    assert loaded.base_issues["A"].labels == ["backend"]


def test_load_sync_state_from_db_returns_none_without_last_sync(tmp_path: Path):
    manager, _conn = _build_manager(tmp_path)
    loaded = manager.load_sync_state_from_db()
    assert loaded is None


def test_create_base_state_from_issue_handles_enum_and_defaults(tmp_path: Path):
    manager = SyncStateManager(tmp_path)
    issue = Issue(id="I1", title="Title", status=Status.TODO, content="Body")

    base = manager.create_base_state_from_issue(issue)

    assert base.id == "I1"
    assert base.status == "todo"
    assert base.description == "Body"


def test_save_base_state_creates_new_state_when_missing(tmp_path: Path):
    manager, _conn = _build_manager(tmp_path)
    issue = Issue(id="I2", title="B", status=Status.CLOSED, content="done")

    assert manager.save_base_state(issue, remote_version=True) is True

    loaded = manager.load_sync_state_from_db()
    assert loaded is not None
    assert loaded.base_issues["I2"].status == "closed"


def test_create_sync_state_from_issues_skips_bad_entries(tmp_path: Path):
    manager = SyncStateManager(tmp_path)
    good = Issue(id="I3", title="ok")
    bad = SimpleNamespace(id="bad")

    state = manager.create_sync_state_from_issues(cast(Any, [good, bad]))

    assert "I3" in state.base_issues
    assert "bad" not in state.base_issues


def test_migrate_json_to_db_behaviors(tmp_path: Path):
    no_db = SyncStateManager(tmp_path)
    assert no_db.migrate_json_to_db() is False

    manager, _conn = _build_manager(tmp_path)
    assert manager.migrate_json_to_db() is True

    manager.state_file.write_text("{}", encoding="utf-8")
    assert manager.migrate_json_to_db() is True
    assert manager.state_file.with_suffix(".json.backup").exists()
