"""Phase 9 contracts for the explicit 0.1.1 workspace migration."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest
import yaml

from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.adapters.outbound.persistence.migration import (
    FilesystemWorkspaceMigration,
)
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
from roadmap.application.use_cases.workspace_migration import WorkspaceMigration

FIXTURE = Path(__file__).parents[3] / "fixtures" / "compatibility" / "v0_1_1"


def _copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    shutil.copytree(FIXTURE, root)
    return root


def _digests(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "canonical-write.lock"
    }


def _migration(root: Path, user_config: Path, **kwargs):
    repository = DocumentRepository(root / ".roadmap")
    projection = SQLiteProjection(root / ".roadmap/db/projection.db", repository)
    adapter = FilesystemWorkspaceMigration(
        root / ".roadmap", projection, user_config, **kwargs
    )
    return WorkspaceMigration(adapter), projection


def test_dry_run_is_byte_for_byte_non_mutating_and_enumerates_complete_write_set(
    tmp_path: Path,
) -> None:
    root = _copy_fixture(tmp_path)
    user_config = tmp_path / "user/config.yaml"
    before = _digests(tmp_path)

    plan = _migration(root, user_config)[0].preflight()

    assert plan.required
    assert not plan.conflicts
    assert plan.source_version == 0
    assert plan.target_version == 1
    assert {item.entity_id for item in plan.changes if item.entity_id} == {
        "a11ce001",
        "5898cb1f",
        "951f146d",
        "v0-1-1",
        "c83ed497",
    }
    assert _digests(tmp_path) == before
    assert not user_config.exists()


def test_migration_preserves_semantics_content_and_ids_then_rebuilds_projection(
    tmp_path: Path,
) -> None:
    root = _copy_fixture(tmp_path)
    roadmap_dir = root / ".roadmap"
    user_config = tmp_path / "user/config.yaml"
    migration, projection = _migration(root, user_config)
    before = {
        (item.kind, item.identity): item.aggregate.content
        for item in DocumentRepository(roadmap_dir).scan()
    }
    plan = migration.preflight()

    result = migration.execute(plan.fingerprint)

    assert result.projection_rebuilt
    expected = {
        "issues/a11ce001.md",
        "issues/5898cb1f.md",
        "issues/951f146d.md",
        "milestones/v0-1-1.md",
        "projects/c83ed497.md",
    }
    actual = {
        str(path.relative_to(roadmap_dir))
        for collection in ("issues", "milestones", "projects")
        for path in (roadmap_dir / collection).glob("*.md")
    }
    assert actual == expected
    migrated = DocumentRepository(roadmap_dir).scan()
    assert {
        (item.kind, item.identity): item.aggregate.content for item in migrated
    } == before
    assert all(item.schema_version == 1 for item in migrated)
    assert (
        next(
            item for item in migrated if item.identity == "a11ce001"
        ).aggregate.retention.value
        == "archived"
    )
    assert (
        "Sanitized fixture comment." in (roadmap_dir / "issues/951f146d.md").read_text()
    )
    assert projection.query()

    project_config = yaml.safe_load((roadmap_dir / "config.yaml").read_text())
    assert project_config == {
        "schema_version": 1,
        "workspace_schema_version": 1,
        "behavior": {
            "default_project_id": "c83ed497",
            "include_closed_in_critical_path": False,
        },
    }
    assert "github" not in project_config
    personal = yaml.safe_load(user_config.read_text())
    assert personal["identity"]["name"] == "fixture-user"
    assert personal["display"]["default_milestone"] == "v0-1-1"

    repeated = migration.preflight()
    assert not repeated.required
    assert not repeated.changes
    assert migration.execute(repeated.fingerprint).already_current


def test_future_workspace_schema_is_rejected_without_changes(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    config = root / ".roadmap/config.yaml"
    config.write_text("workspace_schema_version: 99\n", encoding="utf-8")
    before = _digests(root)

    plan = _migration(root, tmp_path / "user.yaml")[0].preflight()

    assert plan.conflicts == ("workspace schema 99 is newer than supported schema 1",)
    assert _digests(root) == before


def test_permission_loss_stops_preflight_without_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    root = _copy_fixture(tmp_path)
    denied = root / ".roadmap/issues/v0-1-1/951f146d-visible-fixture-issue.md"
    before = _digests(root)
    read_text = Path.read_text

    def permission_error(path: Path, *args, **kwargs):
        if path == denied:
            raise PermissionError("permission denied by fixture")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", permission_error)
    plan = _migration(root, tmp_path / "user.yaml")[0].preflight()

    assert any("cannot read canonical document" in item for item in plan.conflicts)
    assert _digests(root) == before


def test_non_identical_duplicate_stops_preflight(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    source = root / ".roadmap/issues/v0-1-1/951f146d-visible-fixture-issue.md"
    duplicate = root / ".roadmap/issues/other/duplicate.md"
    duplicate.parent.mkdir()
    duplicate.write_text(source.read_text().replace("Visible fixture", "Conflicting"))

    plan = _migration(root, tmp_path / "user.yaml")[0].preflight()

    assert "non-identical duplicate issue id 951f146d" in plan.conflicts


def test_identical_duplicate_is_reconciled_without_guessing(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    source = root / ".roadmap/issues/v0-1-1/951f146d-visible-fixture-issue.md"
    duplicate = root / ".roadmap/issues/other/duplicate.md"
    duplicate.parent.mkdir()
    shutil.copy2(source, duplicate)
    migration, _projection = _migration(root, tmp_path / "user.yaml")

    plan = migration.preflight()

    assert not plan.conflicts
    assert any(item.operation == "delete-duplicate" for item in plan.changes)
    migration.execute(plan.fingerprint)
    assert not duplicate.exists()
    assert (root / ".roadmap/issues/951f146d.md").exists()


def test_corrupt_projection_after_commit_is_a_rebuildable_idempotent_step(
    tmp_path: Path,
) -> None:
    root = _copy_fixture(tmp_path)
    migration, projection = _migration(root, tmp_path / "user.yaml")
    first = migration.preflight()
    migration.execute(first.fingerprint)
    projection.path.write_bytes(b"not sqlite")

    repair = migration.preflight()

    assert [item.operation for item in repair.changes] == ["rebuild"]
    assert migration.execute(repair.fingerprint).projection_rebuilt
    assert projection.query()


def test_failed_canonical_commit_restores_old_layout_and_can_be_retried(
    tmp_path: Path,
) -> None:
    root = _copy_fixture(tmp_path)
    before = _digests(root)
    replacements = 0

    def fail(stage: str, _path: Path | None) -> None:
        nonlocal replacements
        if stage == "after_replace":
            replacements += 1
            if replacements == 2:
                raise OSError("injected migration failure")

    migration, _projection = _migration(
        root, tmp_path / "user/config.yaml", failure_injector=fail
    )
    plan = migration.preflight()
    with pytest.raises(OSError, match="injected migration failure"):
        migration.execute(plan.fingerprint)

    assert _digests(root) == before
    retry, _projection = _migration(root, tmp_path / "user/config.yaml")
    retry_plan = retry.preflight()
    assert retry.execute(retry_plan.fingerprint).target_version == 1


def test_interrupted_migration_rolls_forward_deterministically_on_retry(
    tmp_path: Path,
) -> None:
    root = _copy_fixture(tmp_path)

    def crash(stage: str, _path: Path | None) -> None:
        if stage == "after_replace":
            raise SystemExit("simulated process death")

    migration, _projection = _migration(
        root, tmp_path / "user/config.yaml", failure_injector=crash
    )
    plan = migration.preflight()
    with pytest.raises(SystemExit, match="simulated process death"):
        migration.execute(plan.fingerprint)

    retry, projection = _migration(root, tmp_path / "user/config.yaml")
    retry_plan = retry.preflight()
    result = retry.execute(retry_plan.fingerprint)

    assert result.target_version == 1
    assert projection.query()
    assert not list((root / ".roadmap/db/transactions").glob("*"))
