"""Explicit consent never turns a preview into a write, including damaged state."""

import json
import os
from pathlib import Path

import pytest

from roadmap.bootstrap import cli
from tests.fixtures.cli_workspace import canonical_bytes, seed
from tests.integration.cli.test_cli_migrate_command import _digests, _workspace
from tests.integration.cli.test_cli_mutation_contracts import entity, persistent_bytes


@pytest.mark.parametrize("format_name", ["plain", "json"])
@pytest.mark.parametrize("verbose", [False, True])
def test_projection_preview_with_consent_never_repairs_corrupt_index(
    workspace, cli_runner, format_name, verbose
):
    seed(workspace, entity("issue", "target"))
    projection = workspace.roadmap_dir / "db/projection.db"
    projection.write_bytes(b"corrupt projection")
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(
        cli,
        [
            "health",
            "fix",
            "--fix-type",
            "projection",
            "--dry-run",
            "--yes",
            "--format",
            format_name,
            *(["--verbose"] if verbose else []),
        ],
    )
    assert result.exit_code == 1, result.output
    assert persistent_bytes(workspace) == before
    if format_name == "json":
        assert json.loads(result.stdout)["actions"]
    assert bool(result.stderr) == verbose

    canonical = canonical_bytes(workspace)
    applied = cli_runner.invoke(
        cli, ["health", "fix", "--fix-type", "projection", "--yes", "--format", "json"]
    )
    assert applied.exit_code == 0, applied.output
    assert canonical_bytes(workspace) == canonical
    assert projection.read_bytes() != b"corrupt projection"


@pytest.mark.parametrize("format_name", ["plain", "json"])
@pytest.mark.parametrize("verbose", [False, True])
def test_migration_preview_with_consent_preserves_legacy_and_personal_data(
    cli_runner, tmp_path, monkeypatch, format_name, verbose
):
    root = _workspace(tmp_path, monkeypatch)
    before = _digests(tmp_path)
    result = cli_runner.invoke(
        cli,
        [
            "migrate",
            "--dry-run",
            "--yes",
            "--format",
            format_name,
            *(["--verbose"] if verbose else []),
        ],
    )
    assert result.exit_code == 0, result.output
    if format_name == "json":
        assert json.loads(result.stdout)["required"]
    assert _digests(tmp_path) == before
    assert not (root / ".roadmap/db").exists()


@pytest.mark.parametrize("flags", [["--dry-run", "--yes"], ["--yes"]])
def test_migration_unreadable_canonical_tree_fails_loudly_without_writes(
    cli_runner, tmp_path, monkeypatch, flags
):
    root = _workspace(tmp_path, monkeypatch)
    denied = root / ".roadmap/issues/v0-1-1"
    before = _digests(tmp_path)
    scandir = os.scandir

    def deny(path):
        if Path(path) == denied:
            raise PermissionError("migration canonical enumeration denied")
        return scandir(path)

    with monkeypatch.context() as patch:
        patch.setattr(os, "scandir", deny)
        result = cli_runner.invoke(cli, ["migrate", *flags])
    assert result.exit_code == 1
    assert "migration canonical enumeration denied" in result.stderr
    assert "Traceback" not in result.stderr
    assert _digests(tmp_path) == before


@pytest.mark.parametrize("kind", ["issue", "project", "milestone"])
def test_archive_preview_with_consent_and_override_preserves_all_state(
    workspace, cli_runner, kind
):
    seed(workspace, entity(kind, "target"), entity(kind, "peer"))
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(
        cli, [kind, "archive", "target", "--force", "--yes", "--dry-run", "--verbose"]
    )
    assert result.exit_code == 0, result.output
    assert "preview only" in result.stderr
    assert persistent_bytes(workspace) == before
