"""Real process death, process contention, and CLI recovery guarantees."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from roadmap.adapters.outbound.persistence.canonical import CanonicalUnitOfWork
from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
from roadmap.domain.aggregates import Issue, Milestone
from roadmap.domain.types import EntityId, Name, Timestamp, Title

ROOT = Path(__file__).resolve().parents[3]
WORKER = ROOT / "tests/fixtures/reliability_worker.py"
CLI = Path(sys.executable).parent / "roadmap"


def _environment(workspace: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["XDG_CONFIG_HOME"] = str(workspace / "personal")
    return environment


def _worker(workspace: Path, operation: str, checkpoint: str = "none") -> list[str]:
    return [sys.executable, str(WORKER), str(workspace), operation, checkpoint]


def _run(workspace: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(CLI), *arguments],
        cwd=workspace,
        env=_environment(workspace),
        text=True,
        capture_output=True,
        timeout=15,
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    result = _run(tmp_path, "init", "--skip-project", "--non-interactive")
    assert result.returncode == 0, result.stderr
    now = Timestamp(datetime(2026, 8, 17, tzinfo=UTC))
    repository = DocumentRepository(tmp_path / ".roadmap")
    projection = SQLiteProjection(tmp_path / ".roadmap/db/projection.db", repository)
    with CanonicalUnitOfWork(repository, projection) as unit:
        unit.save_issue(Issue(EntityId("issue-1"), now, now, title=Title("Old issue")))
        unit.save_milestone(
            Milestone(EntityId("milestone-1"), now, now, name=Name("Old milestone"))
        )
        unit.commit()
    return tmp_path


def _canonical(workspace: Path) -> dict[str, bytes]:
    root = workspace / ".roadmap"
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*.md")}


@pytest.mark.parametrize("operation", ["update", "delete"])
@pytest.mark.parametrize(
    "checkpoint", ["after_journal", "after_replace", "before_cleanup"]
)
def test_sigkill_recovers_complete_transaction_on_fresh_process(
    workspace, operation, checkpoint
):
    crashed = subprocess.run(
        _worker(workspace, operation, checkpoint), capture_output=True, timeout=15
    )
    assert crashed.returncode == -signal.SIGKILL, crashed.stderr
    assert list((workspace / ".roadmap/db/transactions").iterdir())
    if checkpoint == "before_cleanup":
        directory = next((workspace / ".roadmap/db/transactions").iterdir())
        assert directory.name.startswith(".completed-")
        # Model a cleanup interrupted after journal deletion: completed intent
        # must never be replayed or require its already-discarded snapshots.
        (directory / "journal.json").unlink()

    restarted = subprocess.run(
        _worker(workspace, "recover"), capture_output=True, timeout=15
    )
    assert restarted.returncode == 0, restarted.stderr
    repository = DocumentRepository(workspace / ".roadmap")
    issue = repository.load("issue", EntityId("issue-1"))
    if operation == "delete":
        assert issue is None
    else:
        milestone = repository.load("milestone", EntityId("milestone-1"))
        assert issue is not None and isinstance(issue.aggregate, Issue)
        assert milestone is not None and isinstance(milestone.aggregate, Milestone)
        assert issue.aggregate.title == "Recovered issue"
        assert milestone.aggregate.name == "Recovered milestone"
    assert not list((workspace / ".roadmap/db/transactions").iterdir())
    before = _canonical(workspace)
    repeated = subprocess.run(
        _worker(workspace, "recover"), capture_output=True, timeout=15
    )
    assert repeated.returncode == 0, repeated.stderr
    assert _canonical(workspace) == before


def test_sigkill_before_prepared_journal_discards_only_uncommitted_intent(workspace):
    before = _canonical(workspace)
    crashed = subprocess.run(
        _worker(workspace, "update", "before_journal"), capture_output=True, timeout=15
    )
    assert crashed.returncode == -signal.SIGKILL
    pending = list((workspace / ".roadmap/db/transactions").iterdir())
    assert len(pending) == 1 and pending[0].name.startswith(".preparing-")
    restarted = subprocess.run(
        _worker(workspace, "recover"), capture_output=True, timeout=15
    )
    assert restarted.returncode == 0, restarted.stderr
    assert _canonical(workspace) == before
    assert not list((workspace / ".roadmap/db/transactions").iterdir())


def test_separate_writer_cannot_steal_lock_and_sigkill_releases_it(workspace):
    before = _canonical(workspace)
    holder = subprocess.Popen(
        _worker(workspace, "hold"), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        deadline = time.monotonic() + 10
        while not (workspace / "writer-ready").exists():
            assert holder.poll() is None, "lock holder exited before becoming ready"
            assert time.monotonic() < deadline, "lock holder did not become ready"
            time.sleep(0.01)
        contender = subprocess.run(
            _worker(workspace, "update"), capture_output=True, timeout=15
        )
        assert contender.returncode != 0
        assert b"workspace lock timed out" in contender.stderr
        assert _canonical(workspace) == before
    finally:
        holder.kill()
        holder.communicate(timeout=5)
    successor = subprocess.run(
        _worker(workspace, "update"), capture_output=True, timeout=15
    )
    assert successor.returncode == 0, successor.stderr
    assert _canonical(workspace) != before


def test_cli_previews_then_recovers_interrupted_transaction(workspace):
    crashed = subprocess.run(
        _worker(workspace, "update", "after_replace"), capture_output=True, timeout=15
    )
    assert crashed.returncode == -signal.SIGKILL
    before = _canonical(workspace)
    health = _run(workspace, "health", "--format", "json")
    assert health.returncode == 2, health.stderr
    assert "transaction.interrupted" in {
        f["finding_id"] for f in json.loads(health.stdout)["findings"]
    }
    preview = _run(workspace, "health", "fix", "--dry-run", "--format", "json")
    assert preview.returncode == 2, preview.stderr
    assert _canonical(workspace) == before
    assert list((workspace / ".roadmap/db/transactions").iterdir())
    repaired = _run(workspace, "health", "fix", "--yes", "--format", "json")
    assert repaired.returncode == 0, repaired.stderr
    final = _run(workspace, "health", "--format", "json")
    assert final.returncode == 0, final.stderr
    assert json.loads(final.stdout)["status"] == "healthy"
    assert not list((workspace / ".roadmap/db/transactions").iterdir())


def test_cli_recovery_refuses_to_overwrite_post_crash_manual_edit(workspace):
    crashed = subprocess.run(
        _worker(workspace, "update", "after_journal"), capture_output=True, timeout=15
    )
    assert crashed.returncode == -signal.SIGKILL
    issue = workspace / ".roadmap/issues/issue-1.md"
    issue.write_text(issue.read_text().replace("Old issue", "Manually corrected issue"))
    before = _canonical(workspace)
    repaired = _run(workspace, "health", "fix", "--yes")
    assert repaired.returncode != 0
    assert "cannot recover transaction" in repaired.stderr
    assert _canonical(workspace) == before
    assert list((workspace / ".roadmap/db/transactions").iterdir())


def test_two_cli_writers_preserve_both_comments(workspace):
    processes = [
        subprocess.Popen(
            [str(CLI), "issue", "comment", "add", "issue-1", text],
            cwd=workspace,
            env=_environment(workspace),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for text in ("First writer", "Second writer")
    ]
    try:
        for process in processes:
            _stdout, stderr = process.communicate(timeout=15)
            assert process.returncode == 0, stderr
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)
    envelope = DocumentRepository(workspace / ".roadmap").load(
        "issue", EntityId("issue-1")
    )
    assert envelope is not None and isinstance(envelope.aggregate, Issue)
    assert {comment.body for comment in envelope.aggregate.comments} == {
        "First writer",
        "Second writer",
    }


@pytest.mark.parametrize("damage", ["missing", "corrupt", "truncated"])
def test_cli_projection_repair_preserves_canonical_bytes(workspace, damage):
    projection = workspace / ".roadmap/db/projection.db"
    before = _canonical(workspace)
    if damage == "missing":
        projection.unlink()
    elif damage == "corrupt":
        projection.write_bytes(b"not sqlite")
    else:
        projection.write_bytes(projection.read_bytes()[:40])
    health = _run(workspace, "health", "--format", "json")
    assert health.returncode == 1, health.stderr
    assert _canonical(workspace) == before
    assert _run(workspace, "health", "fix", "--dry-run").returncode == 1
    assert _canonical(workspace) == before
    repaired = _run(workspace, "health", "fix", "--yes")
    assert repaired.returncode == 0, repaired.stderr
    assert _run(workspace, "health", "--format", "json").returncode == 0
    assert _canonical(workspace) == before
    assert _run(workspace, "issue", "view", "issue-1").returncode == 0


@pytest.mark.parametrize(
    "checkpoint", ["after_journal", "after_replace", "after_canonical_commit"]
)
def test_sigkill_migration_retries_without_losing_ids_or_content(tmp_path, checkpoint):
    shutil.copytree(
        ROOT / "tests/fixtures/compatibility/v0_1_1", tmp_path, dirs_exist_ok=True
    )
    repository = DocumentRepository(tmp_path / ".roadmap")
    before = {(e.kind, e.identity): e.aggregate.content for e in repository.scan()}
    crashed = subprocess.run(
        _worker(tmp_path, "migration", checkpoint), capture_output=True, timeout=15
    )
    assert crashed.returncode == -signal.SIGKILL, crashed.stderr
    retry = subprocess.run(
        _worker(tmp_path, "migration"), capture_output=True, timeout=15
    )
    assert retry.returncode == 0, retry.stderr
    assert {
        (e.kind, e.identity): e.aggregate.content for e in repository.scan()
    } == before
    assert all(e.schema_version == 1 for e in repository.scan())
    assert (tmp_path / ".roadmap/db/projection.db").is_file()
    assert not list((tmp_path / ".roadmap/db/transactions").iterdir())
    repeated = subprocess.run(
        _worker(tmp_path, "migration"), capture_output=True, timeout=15
    )
    assert repeated.returncode == 0, repeated.stderr
