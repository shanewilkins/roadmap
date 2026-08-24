"""Installed-style CLI coverage for explicit Phase 9 migration."""

import hashlib
import json
import shutil
from pathlib import Path

import yaml

from roadmap.bootstrap import cli

FIXTURE = Path(__file__).parents[2] / "fixtures" / "compatibility" / "v0_1_1"


def _workspace(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "workspace"
    shutil.copytree(FIXTURE, root)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(root)
    return root


def _digests(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_cli_dry_run_is_machine_readable_and_does_not_construct_legacy_core(
    cli_runner, tmp_path, monkeypatch
) -> None:
    root = _workspace(tmp_path, monkeypatch)
    before = _digests(root)

    result = cli_runner.invoke(cli, ["migrate", "--dry-run", "--format", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["required"] is True
    assert payload["conflicts"] == []
    assert _digests(root) == before
    assert not (root / ".roadmap/db").exists()


def test_cli_executes_only_after_explicit_confirmation_and_is_idempotent(
    cli_runner, tmp_path, monkeypatch
) -> None:
    root = _workspace(tmp_path, monkeypatch)

    migrated = cli_runner.invoke(cli, ["migrate", "--yes", "--format", "json"])
    repeated = cli_runner.invoke(cli, ["migrate", "--yes", "--format", "json"])

    assert migrated.exit_code == 0, migrated.output
    payload = json.loads(migrated.stdout)
    assert payload["status"] == "migrated"
    assert payload["projection_rebuilt"] is True
    assert (root / ".roadmap/issues/951f146d.md").exists()
    assert repeated.exit_code == 0
    assert json.loads(repeated.stdout)["required"] is False


def test_cli_rejects_future_workspace_without_mutation(
    cli_runner, tmp_path, monkeypatch
) -> None:
    root = _workspace(tmp_path, monkeypatch)
    config = root / ".roadmap/config.yaml"
    values = yaml.safe_load(config.read_text())
    values["workspace_schema_version"] = 2
    config.write_text(yaml.safe_dump(values))
    before = _digests(root)

    result = cli_runner.invoke(cli, ["migrate", "--yes"])

    assert result.exit_code == 1
    assert "newer than supported" in result.output
    assert _digests(root) == before
