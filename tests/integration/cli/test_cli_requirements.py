"""Real-storage optional adoption, stable requirement identity and safe editing."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
import yaml

from roadmap.adapters.outbound.persistence.canonical import CanonicalUnitOfWork
from roadmap.adapters.outbound.persistence.configuration import (
    ConfigurationError,
    _read,
)
from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.bootstrap import cli
from roadmap.domain.requirements import Requirement, RequirementKey
from tests.fixtures.cli_workspace import run


def canonical(workspace):
    return {
        p: p.read_bytes()
        for p in workspace.roadmap_dir.rglob("*")
        if p.is_file() and p.suffix in {".md", ".yaml"}
    }


def command(runner, *args):
    return json.loads(run(runner, "requirement", *args).stdout)


def create(runner, **kwargs):
    args = [
        "create",
        "--type",
        "user",
        "--title",
        "Keep intent",
        "--statement",
        "Full **Markdown**\n",
        "--criterion",
        "C1=Preserve original UUID",
    ]
    for key, value in kwargs.items():
        args.extend(["--" + key.replace("_", "-"), value])
    return command(runner, *args)["requirement"]


def enable(runner):
    return command(runner, "enable", "--apply")


def test_adoption_preview_and_repeat_preserve_issue_only_workspace(
    workspace, cli_runner
):
    before = canonical(workspace)
    assert command(cli_runner, "list")["requirements"] == []
    assert not command(cli_runner, "enable")["enabled"]
    assert canonical(workspace) == before
    failed = cli_runner.invoke(
        cli,
        [
            "requirement",
            "create",
            "--type",
            "user",
            "--title",
            "T",
            "--statement",
            "S",
            "--criterion",
            "C1=Criterion",
        ],
    )
    assert failed.exit_code == 1 and "Enable requirements explicitly" in failed.stderr
    assert canonical(workspace) == before
    assert enable(cli_runner)["enabled"]
    project = workspace.roadmap_dir / "config.yaml"
    assert yaml.safe_load(project.read_text())["workspace_schema_version"] == 2
    # The released reader accepts at most configuration schema 1; the new
    # adapter only permits schema 2 explicitly for project configuration.
    with pytest.raises(ConfigurationError, match="unsupported configuration"):
        _read(project)
    after = canonical(workspace)
    enable(cli_runner)
    assert canonical(workspace) == after
    run(
        cli_runner,
        "config",
        "set",
        "behavior.include_closed_in_critical_path",
        "true",
        "--project",
    )
    assert yaml.safe_load(project.read_text())["schema_version"] == 2


def test_create_edit_rekey_manual_edit_and_unknown_fields(workspace, cli_runner):
    enable(cli_runner)
    first = create(cli_runner, owner="Alice", journey="J-10", stage="Capture")
    identity = first["id"]
    path = workspace.roadmap_dir / f"requirements/{identity}.md"
    assert first["key"] == "UR-001" and first["status"] == "draft"
    before = canonical(workspace)
    assert command(cli_runner, "view", "UR-001")["requirement"]["id"] == identity
    assert canonical(workspace) == before
    command(cli_runner, "update", identity, "--priority", "high", "--owner", "Bob")
    meta = command(cli_runner, "view", identity)["requirement"]
    assert meta["current_revision"] == first["current_revision"]
    assert len(meta["revisions"]) == 1
    command(cli_runner, "rekey", identity, "--key", "UR-012")
    assert path.exists()
    assert command(cli_runner, "view", "UR-012")["requirement"]["id"] == identity
    raw = path.read_text().replace(
        "schema_version: 1", "schema_version: 1\ncustom: preserved"
    )
    path.write_text(raw.replace("Full **Markdown**\n", "Manually **revised**\n", 1))
    before = canonical(workspace)
    manual = command(cli_runner, "view", identity)["requirement"]
    assert manual["uncaptured_intent"]
    assert canonical(workspace) == before
    command(cli_runner, "update", identity, "--title", "Revised title")
    updated = command(cli_runner, "view", identity)["requirement"]
    assert len(updated["revisions"]) == 3
    assert updated["history"][: len(first["history"])] == first["history"]
    assert "custom: preserved" in path.read_text()
    assert (
        command(
            cli_runner,
            "list",
            "--type",
            "user",
            "--journey",
            "J-10",
            "--stage",
            "Capture",
            "--priority",
            "high",
            "--owner",
            "Bob",
            "--search",
            "revised",
        )["requirements"][0]["id"]
        == identity
    )
    run(cli_runner, "health", "fix", "--fix-type", "projection", "--yes")
    assert command(cli_runner, "view", identity)["requirement"] == updated


def test_branch_collision_repair_preserves_ids_and_paths(workspace, cli_runner):
    enable(cli_runner)
    first, second = create(cli_runner), create(cli_runner)
    repository = DocumentRepository(workspace.roadmap_dir)
    original = next(
        x.aggregate
        for x in repository.scan("requirement")
        if x.identity == second["id"]
    )
    assert isinstance(original, Requirement)
    # Model a merged independently allocated alias through fixture injection.
    with CanonicalUnitOfWork(repository) as unit:
        unit.save_requirement(replace(original, key=RequirementKey(first["key"])))
        unit.commit()
    failed = cli_runner.invoke(cli, ["requirement", "view", "UR-001"])
    assert failed.exit_code == 1 and "alias collision" in failed.stderr
    before = canonical(workspace)
    assert (
        command(cli_runner, "view", second["id"])["requirement"]["id"] == second["id"]
    )
    assert canonical(workspace) == before
    command(cli_runner, "rekey", second["id"], "--key", "UR-002")
    assert {x["id"] for x in command(cli_runner, "list")["requirements"]} == {
        first["id"],
        second["id"],
    }
    assert len(list((workspace.roadmap_dir / "requirements").glob("*.md"))) == 2


def test_concurrent_creates_allocate_distinct_aliases_under_existing_lock(
    workspace, cli_runner
):
    enable(cli_runner)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                workspace.requirements.create,
                kind="user",
                title="T",
                statement="S",
                criterion_values=("C1=Coverage",),
            )
            for _ in range(2)
        ]
        records = [future.result(timeout=20).requirement for future in futures]
    assert {str(x.key) for x in records} == {"UR-001", "UR-002"}
    assert len({str(x.id) for x in records}) == 2


def test_expected_revision_and_git_conflict_refuse_without_mutation(
    workspace, cli_runner
):
    enable(cli_runner)
    record = create(cli_runner)
    before = canonical(workspace)
    failed = cli_runner.invoke(
        cli,
        [
            "requirement",
            "update",
            record["id"],
            "--title",
            "Changed",
            "--expected-revision",
            "wrong",
        ],
    )
    assert failed.exit_code == 1 and "changed" in failed.stderr
    assert canonical(workspace) == before
    path = workspace.roadmap_dir / f"requirements/{record['id']}.md"
    path.write_text(
        path.read_text()
        + "\n<<<<<<< ours\nStatement A\n=======\nStatement B\n>>>>>>> theirs\n"
    )
    before = canonical(workspace)
    failed = cli_runner.invoke(
        cli, ["requirement", "update", record["id"], "--title", "Changed"]
    )
    assert failed.exit_code == 1 and "conflict" in failed.stderr
    assert canonical(workspace) == before


def test_external_edit_during_write_is_preserved(workspace, cli_runner, monkeypatch):
    enable(cli_runner)
    record = create(cli_runner)
    path = workspace.roadmap_dir / f"requirements/{record['id']}.md"
    original = CanonicalUnitOfWork.save_requirement

    def racing_save(unit, requirement):
        original(unit, requirement)
        path.write_text(path.read_text() + "\nExternal edit survives\n")

    monkeypatch.setattr(CanonicalUnitOfWork, "save_requirement", racing_save)
    failed = cli_runner.invoke(
        cli, ["requirement", "update", record["id"], "--title", "Changed"]
    )
    assert failed.exit_code == 1
    assert "External edit survives" in path.read_text()
    assert "title: Keep intent" in path.read_text()


def test_technical_lookup_filters_and_invalid_edits_are_atomic(workspace, cli_runner):
    enable(cli_runner)
    record = command(
        cli_runner,
        "create",
        "--type",
        "technical",
        "--title",
        "Unicode café",
        "--statement",
        "Keep Δ and **Markdown**",
        "--criterion",
        "V1=Round-trip bytes",
        "--key",
        "TR-050",
        "--priority",
        "low",
    )["requirement"]
    assert (
        command(
            cli_runner,
            "list",
            "--type",
            "technical",
            "--status",
            "draft",
            "--search",
            "CAFÉ",
            "--sort",
            "title",
        )["requirements"][0]["id"]
        == record["id"]
    )
    before = canonical(workspace)
    failures = [
        ("view", "TR-999"),
        ("rekey", "TR-050", "--key", "TR-051"),
        ("rekey", record["id"], "--key", "UR-050"),
        ("update", record["id"], "--criterion", "V1=A", "--criterion", "V1=B"),
        (
            "create",
            "--type",
            "technical",
            "--title",
            "T",
            "--statement",
            "S",
            "--criterion",
            "V1=C",
            "--key",
            "TR-050",
        ),
    ]
    for args in failures:
        result = cli_runner.invoke(cli, ["requirement", *args])
        assert result.exit_code != 0
        assert canonical(workspace) == before


@pytest.mark.parametrize("stage", ["before_validate", "after_replace"])
def test_interrupted_capture_recovers_without_lost_history(
    workspace, cli_runner, monkeypatch, stage
):
    enable(cli_runner)
    record = create(cli_runner)
    original_commit = CanonicalUnitOfWork.commit

    def fail(current, _path):
        if current == stage:
            raise OSError("injected requirement transaction failure")

    def commit(unit):
        unit._inject = fail
        return original_commit(unit)

    with monkeypatch.context() as patch:
        patch.setattr(CanonicalUnitOfWork, "commit", commit)
        failed = cli_runner.invoke(
            cli, ["requirement", "update", record["id"], "--title", "Recovered title"]
        )
        assert failed.exit_code == 1
    command(cli_runner, "update", record["id"], "--title", "Recovered title")
    recovered = command(cli_runner, "view", record["id"])["requirement"]
    assert recovered["id"] == record["id"]
    assert len(recovered["revisions"]) == 2
    assert recovered["history"][0] == record["history"][0]
    assert len(list((workspace.roadmap_dir / "requirements").glob("*.md"))) == 1


def test_application_update_cannot_rebind_identity_or_forge_history(
    workspace, cli_runner
):
    from roadmap.application.failures import ApplicationFailure

    enable(cli_runner)
    record = create(cli_runner)
    before = canonical(workspace)
    for field, value in [
        ("id", "replacement"),
        ("history", ()),
        ("revisions", ()),
        ("key", "UR-099"),
        ("created", None),
        ("status", "verified"),
    ]:
        with pytest.raises(ApplicationFailure, match="Unsupported requirement fields"):
            workspace.requirements.update(record["id"], **{field: value})
        assert canonical(workspace) == before


def test_unchanged_updates_rekeys_and_adoption_retries_write_nothing(
    workspace, cli_runner
):
    enable(cli_runner)
    record = create(cli_runner)
    before = canonical(workspace)
    command(cli_runner, "update", record["id"], "--title", "Keep intent")
    command(cli_runner, "rekey", record["id"], "--key", "UR-001")
    assert canonical(workspace) == before
    run(cli_runner, "config", "reset", "--project", "--yes")
    assert (
        yaml.safe_load((workspace.roadmap_dir / "config.yaml").read_text())[
            "schema_version"
        ]
        == 2
    )


@pytest.mark.parametrize("stage", ["before_validate", "after_replace"])
def test_interrupted_adoption_safely_retries(workspace, cli_runner, monkeypatch, stage):
    original_commit = CanonicalUnitOfWork.commit

    def fail(current, _path):
        if current == stage:
            raise OSError("injected adoption transaction failure")

    def commit(unit):
        unit._inject = fail
        return original_commit(unit)

    with monkeypatch.context() as patch:
        patch.setattr(CanonicalUnitOfWork, "commit", commit)
        failed = cli_runner.invoke(cli, ["requirement", "enable", "--apply"])
        assert failed.exit_code == 1
    enable(cli_runner)
    after = canonical(workspace)
    enable(cli_runner)
    assert canonical(workspace) == after
    assert command(cli_runner, "list")["requirements"] == []


def test_adoption_preserves_external_configuration_edit(
    workspace, cli_runner, monkeypatch
):
    original_stage = CanonicalUnitOfWork.stage_file
    path = workspace.roadmap_dir / "config.yaml"

    def racing_stage(unit, relative, content, **kwargs):
        path.write_text(path.read_text() + "\n# External configuration edit survives\n")
        return original_stage(unit, relative, content, **kwargs)

    monkeypatch.setattr(CanonicalUnitOfWork, "stage_file", racing_stage)
    failed = cli_runner.invoke(cli, ["requirement", "enable", "--apply"])
    assert failed.exit_code == 1
    assert "External configuration edit survives" in path.read_text()
    assert yaml.safe_load(path.read_text())["schema_version"] == 1
