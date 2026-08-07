"""Tests for helper functions in sync_context module."""

import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from roadmap.adapters.cli import sync_context
from roadmap.core.services.sync.sync_state import IssueBaseState, SyncState


def _core(tmp_path: Path):
    core = Mock()
    core.roadmap_dir = tmp_path
    core.db_dir = tmp_path / ".roadmap" / "db"
    core.issues_dir = tmp_path / "issues"
    return core


def test_resolve_backend_and_init_defaults_to_git(tmp_path: Path):
    core = _core(tmp_path)
    backend = Mock(return_value="backend_obj")

    backend_type, sync_backend = sync_context._resolve_backend_and_init(
        core, None, backend
    )

    assert backend_type == "git"
    assert sync_backend == "backend_obj"
    backend.assert_called_once_with("git", core, {})


def test_resolve_backend_and_init_uses_github_config_and_token(
    tmp_path: Path, monkeypatch
):
    core = _core(tmp_path)
    (tmp_path / "config.yaml").write_text(
        "github:\n  sync_backend: github\n  owner: me\n  repo: project\n",
        encoding="utf-8",
    )

    class _CredManager:
        def get_token(self):
            return "secret"

    monkeypatch.setattr(
        "roadmap.infrastructure.security.credentials.CredentialManager", _CredManager
    )
    backend = Mock(return_value="gh")

    backend_type, sync_backend = sync_context._resolve_backend_and_init(
        core, None, backend
    )

    assert backend_type == "github"
    assert sync_backend == "gh"
    args = backend.call_args[0]
    assert args[0] == "github"
    assert args[2]["token"] == "secret"


def test_clear_baseline_db_deletes_rows(tmp_path: Path):
    core = _core(tmp_path)
    core.db_dir.mkdir(parents=True, exist_ok=True)
    db_path = core.db_dir / "state.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE sync_base_state (id INTEGER PRIMARY KEY, data TEXT)")
    conn.execute("INSERT INTO sync_base_state (data) VALUES ('x')")
    conn.commit()
    conn.close()
    console = Mock()

    sync_context._clear_baseline_db(core, console)

    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM sync_base_state").fetchone()[0]
    conn.close()
    assert count == 0


def test_create_and_save_baseline_success(monkeypatch):
    core = Mock()
    core.roadmap_dir = Path("/tmp/roadmap")
    baseline = SyncState(
        base_issues={
            "A": IssueBaseState(
                id="A", status="todo", title="Title", headline="h", content="c"
            )
        }
    )
    orchestrator = Mock()
    orchestrator._create_initial_baseline.return_value = baseline
    monkeypatch.setattr(
        "roadmap.adapters.sync.sync_retrieval_orchestrator.SyncRetrievalOrchestrator",
        Mock(return_value=orchestrator),
    )
    core.db.save_sync_baseline.return_value = True
    console = Mock()

    ok = sync_context._create_and_save_baseline(core, Mock(), "github", console, False)

    assert ok is True
    core.db.save_sync_baseline.assert_called_once()


def test_prune_db_issues_missing_files_dry_run_and_apply(tmp_path: Path, monkeypatch):
    core = _core(tmp_path)
    core.issues_dir.mkdir(parents=True, exist_ok=True)
    (core.issues_dir / "A.md").write_text("# A", encoding="utf-8")
    core.db_dir.mkdir(parents=True, exist_ok=True)
    db_path = core.db_dir / "state.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE issues (id TEXT PRIMARY KEY)")
    conn.executemany("INSERT INTO issues (id) VALUES (?)", [("A",), ("B",)])
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        "roadmap.adapters.persistence.parser.issue.IssueParser.parse_issue_file",
        lambda file_path: SimpleNamespace(id=file_path.stem),
    )

    console = Mock()
    sync_context._prune_db_issues_missing_files(core, console, dry_run=True)
    conn = sqlite3.connect(db_path)
    count_dry = conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
    conn.close()
    assert count_dry == 2

    sync_context._prune_db_issues_missing_files(core, console, dry_run=False)
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id FROM issues ORDER BY id").fetchall()
    conn.close()
    assert rows == [("A",)]


def test_repair_remote_links_github_flow_and_dry_run(tmp_path: Path):
    core = _core(tmp_path)
    core.validation.collect_remote_link_validation_data.return_value = {
        "yaml_remote_ids": {"A": "10"},
        "db_links": {},
    }
    core.validation.build_remote_link_report.return_value = {
        "missing_in_db": ["A"],
        "extra_in_db": [],
        "duplicate_remote_ids": [],
    }
    core.validation.apply_remote_link_fixes.return_value = {
        "fixed_count": 1,
        "removed_count": 0,
        "deduped_count": 0,
    }
    console = Mock()

    sync_context._repair_remote_links(core, console, "github", dry_run=False)
    core.validation.apply_remote_link_fixes.assert_called_once()

    core.validation.apply_remote_link_fixes.reset_mock()
    sync_context._repair_remote_links(core, console, "github", dry_run=True)
    core.validation.apply_remote_link_fixes.assert_not_called()
