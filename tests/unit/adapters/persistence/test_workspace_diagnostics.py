"""Contracts for read-only diagnosis and bounded workspace repair."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from roadmap.adapters.outbound.persistence.diagnostics import (
    FilesystemWorkspaceDiagnostics,
)
from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
from roadmap.application.failures import ApplicationFailure, FailureCategory


def _issue(path, *, milestone_id=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime(2026, 8, 24, tzinfo=UTC).isoformat()
    values = {
        "schema_version": 1,
        "id": path.stem,
        "title": "Diagnose me",
        "status": "todo",
        "priority": "medium",
        "issue_type": "other",
        "created": now,
        "updated": now,
        "milestone": milestone_id,
    }
    path.write_text(
        f"---\n{yaml.safe_dump(values, sort_keys=False).rstrip()}\n---\nBody\n",
        encoding="utf-8",
    )


def _diagnostics(tmp_path):
    root = tmp_path / ".roadmap"
    repository = DocumentRepository(root)
    projection = SQLiteProjection(root / "db/projection.db", repository)
    return FilesystemWorkspaceDiagnostics(repository, projection), projection


def test_scan_is_read_only_and_reports_missing_projection(tmp_path):
    _issue(tmp_path / ".roadmap/issues/issue-1.md")
    diagnostics, projection = _diagnostics(tmp_path)

    report = diagnostics.scan()

    assert report.exit_code == 1
    assert [item.finding_id for item in report.findings] == ["projection.not-current"]
    assert not projection.path.exists()


def test_projection_repair_is_previewable_and_post_check_is_clean(tmp_path):
    _issue(tmp_path / ".roadmap/issues/issue-1.md")
    diagnostics, projection = _diagnostics(tmp_path)

    actions = diagnostics.preview("projection")
    assert [item.action_id for item in actions] == ["rebuild-projection"]
    assert not projection.path.exists()

    diagnostics.apply(actions)

    assert projection.path.exists()
    assert diagnostics.scan().exit_code == 0


def test_invalid_canonical_document_blocks_projection_repair(tmp_path):
    path = tmp_path / ".roadmap/issues/broken.md"
    path.parent.mkdir(parents=True)
    path.write_text("<<<<<<< ours\n=======\n>>>>>>> theirs\n", encoding="utf-8")
    diagnostics, projection = _diagnostics(tmp_path)

    report = diagnostics.scan()

    assert report.exit_code == 2
    assert report.findings[0].finding_id == "canonical.git-conflict"
    assert diagnostics.preview("projection") == ()
    assert not projection.path.exists()


def test_broken_relationship_identifies_both_entities(tmp_path):
    _issue(tmp_path / ".roadmap/issues/issue-1.md", milestone_id="missing")
    diagnostics, _projection = _diagnostics(tmp_path)

    report = diagnostics.scan()

    finding = next(
        item
        for item in report.findings
        if item.finding_id == "canonical.broken-reference"
    )
    assert finding.entity_id == "issue-1"
    assert "missing" in finding.message


def test_permission_denied_is_a_stable_finding(tmp_path, monkeypatch):
    path = tmp_path / ".roadmap/issues/issue-1.md"
    _issue(path)
    diagnostics, _projection = _diagnostics(tmp_path)
    original = Path.read_text

    def deny_issue(target, *args, **kwargs):
        if target == path:
            raise PermissionError("denied")
        return original(target, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", deny_issue)

    report = diagnostics.scan()

    finding = next(
        item for item in report.findings if item.scope == "issues/issue-1.md"
    )
    assert finding.finding_id == "canonical.unreadable"
    assert finding.severity.value == "critical"


def test_interrupted_recovery_is_previewable_repeatable_and_validated(tmp_path):
    diagnostics, _projection = _diagnostics(tmp_path)
    transaction = tmp_path / ".roadmap/db/transactions/interrupted"
    transaction.mkdir(parents=True)
    (transaction / "0.after").write_text("recovered\n", encoding="utf-8")
    (transaction / "journal.json").write_text(
        json.dumps(
            {
                "state": "prepared",
                "entries": [
                    {
                        "target": "artifacts/recovered.txt",
                        "before": None,
                        "after": "0.after",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    actions = diagnostics.preview("recovery")
    diagnostics.apply(actions)

    assert [item.action_id for item in actions] == ["recover-interrupted-transactions"]
    assert (tmp_path / ".roadmap/artifacts/recovered.txt").read_text() == "recovered\n"
    assert diagnostics.preview("recovery") == ()
    assert not transaction.exists()


@pytest.mark.parametrize(
    "damage,finding",
    [
        ("duplicate", "canonical.duplicate-id"),
        ("wrong-path", "canonical.noncanonical-path"),
        ("malformed", "canonical.invalid"),
    ],
)
def test_ambiguous_or_damaged_canonical_state_blocks_projection_repair(
    tmp_path, damage, finding
):
    path = tmp_path / ".roadmap/issues/issue-1.md"
    _issue(path)
    if damage == "duplicate":
        other = path.with_name("other.md")
        other.write_bytes(path.read_bytes())
    elif damage == "wrong-path":
        path.rename(path.with_name("wrong.md"))
    else:
        path.write_text("---\nnot: [valid\n---\nBody\n")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*.md")}
    diagnostics, projection = _diagnostics(tmp_path)
    assert finding in {f.finding_id for f in diagnostics.scan().findings}
    assert diagnostics.preview("projection") == ()
    assert not projection.path.exists()
    assert {p: p.read_bytes() for p in tmp_path.rglob("*.md")} == before


def test_unreadable_journal_directory_is_critical_and_not_silently_skipped(
    tmp_path, monkeypatch
):
    _issue(tmp_path / ".roadmap/issues/issue-1.md")
    root = tmp_path / ".roadmap/db/transactions"
    root.mkdir(parents=True)
    original = Path.iterdir

    def iterdir(path):
        if path == root:
            raise PermissionError("injected journal denial")
        return original(path)

    monkeypatch.setattr(Path, "iterdir", iterdir)
    diagnostics, projection = _diagnostics(tmp_path)
    finding = next(
        f
        for f in diagnostics.scan().findings
        if f.finding_id == "transaction.unreadable"
    )
    assert finding.severity.value == "critical"
    with pytest.raises(ApplicationFailure) as captured:
        diagnostics.preview("recovery")
    assert captured.value.category is FailureCategory.STORAGE_UNAVAILABLE
    assert diagnostics.preview("projection") == ()
    assert not projection.path.exists()


def test_projection_inspection_failure_is_reported_and_repair_is_blocked(
    tmp_path, monkeypatch
):
    _issue(tmp_path / ".roadmap/issues/issue-1.md")
    diagnostics, projection = _diagnostics(tmp_path)

    def fail_inspection():
        raise PermissionError("injected projection denial")

    monkeypatch.setattr(projection, "inspect_state", fail_inspection)
    report = diagnostics.scan()
    assert report.exit_code == 2
    assert [f.finding_id for f in report.findings] == ["projection.unreadable"]
    assert diagnostics.preview("projection") == ()
    assert not projection.path.exists()


def test_failed_projection_repair_is_storage_unavailable_and_preserves_data(
    tmp_path, monkeypatch
):
    path = tmp_path / ".roadmap/issues/issue-1.md"
    _issue(path)
    before = path.read_bytes()
    diagnostics, projection = _diagnostics(tmp_path)
    actions = diagnostics.preview("projection")

    def fail_rebuild():
        raise OSError("injected repair failure")

    monkeypatch.setattr(projection, "rebuild", fail_rebuild)
    with pytest.raises(ApplicationFailure) as captured:
        diagnostics.apply(actions)
    assert captured.value.category is FailureCategory.STORAGE_UNAVAILABLE
    assert "injected repair failure" in str(captured.value)
    assert path.read_bytes() == before
    assert not projection.path.exists()
