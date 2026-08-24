"""Contracts for read-only diagnosis and bounded workspace repair."""

import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

from roadmap.adapters.outbound.persistence.diagnostics import (
    FilesystemWorkspaceDiagnostics,
)
from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection


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
