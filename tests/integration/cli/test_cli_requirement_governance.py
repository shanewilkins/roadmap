"""Canonical lifecycle/evidence journeys, preservation and atomic refusal."""

import sqlite3
from contextlib import closing

import pytest
import yaml

from roadmap.adapters.outbound.persistence.canonical import CanonicalUnitOfWork
from roadmap.bootstrap import cli
from tests.fixtures.cli_workspace import run
from tests.integration.cli.test_cli_requirements import (
    canonical,
    command,
    create,
    enable,
)


def setup_requirement(runner):
    enable(runner)
    record = create(runner)
    return command(
        runner,
        "update",
        record["id"],
        "--criterion",
        "C1=Preserve UUID",
        "--criterion",
        "C2=Preserve history",
    )["requirement"]


def transition(runner, record, status, **kwargs):
    return command(
        runner,
        "transition",
        record["id"],
        "--status",
        status,
        "--expected-revision",
        record["current_revision"],
        "--reason",
        kwargs.get("reason", "Reviewed acceptance and results"),
    )["requirement"]


def evidence(runner, record, criterion="C1", result="pass"):
    return command(
        runner,
        "evidence",
        record["id"],
        "--criterion",
        criterion,
        "--result",
        result,
        "--reference",
        "commit:abc123",
        "--expected-revision",
        record["current_revision"],
        "--note",
        "Actual result",
        "--acceptance-id",
        record["active_acceptance_id"],
    )["requirement"]


def verify(runner, record):
    accepted = transition(runner, record, "accepted")
    first = evidence(runner, accepted)
    second = evidence(runner, first, "C2")
    return transition(runner, second, "verified")


def test_complete_lifecycle_evidence_preserves_attribution_and_rebuild(
    workspace, cli_runner
):
    record = setup_requirement(cli_runner)
    accepted = transition(cli_runner, record, "accepted")
    assert accepted["acceptance_current"] and len(accepted["acceptances"]) == 1
    cycle = accepted["acceptances"][0]
    assert cycle["actor"] and cycle["at"] and cycle["reason"]
    assert cycle["revision"] == record["current_revision"]
    transition(cli_runner, accepted, "in-progress")
    first = evidence(cli_runner, accepted)
    entry = first["evidence"][0]
    assert entry["acceptance_id"] == cycle["id"]
    assert entry["reference"] == "commit:abc123" and entry["note"] == "Actual result"
    assert entry["actor"] and entry["at"]
    evidence(cli_runner, first, "C2")
    current = transition(cli_runner, first, "verified")
    assert current["verification"] == {"C1": "pass", "C2": "pass"}
    assert current["status"] == "verified"
    before = canonical(workspace)
    assert command(cli_runner, "list", "--status", "verified")["requirements"] == [
        current
    ]
    assert canonical(workspace) == before
    run(cli_runner, "health", "fix", "--fix-type", "projection", "--yes")
    assert command(cli_runner, "view", record["id"])["requirement"] == current
    assert canonical(workspace) == before


def test_failed_incomplete_and_missing_evidence_refuse_verification(
    workspace, cli_runner
):
    record = transition(cli_runner, setup_requirement(cli_runner), "accepted")
    for criterion, result in [("C1", "pass"), ("C2", "incomplete"), ("C2", "fail")]:
        record = evidence(cli_runner, record, criterion, result)
        before = canonical(workspace)
        failed = cli_runner.invoke(
            cli,
            [
                "requirement",
                "transition",
                record["id"],
                "--status",
                "verified",
                "--expected-revision",
                record["current_revision"],
                "--reason",
                "Check",
            ],
        )
        assert failed.exit_code == 1 and "every criterion" in failed.stderr
        assert canonical(workspace) == before
    record = evidence(cli_runner, record, "C2")
    record = transition(cli_runner, record, "verified")
    record = evidence(cli_runner, record, "C1", "fail")
    assert record["status"] == "in-progress"
    record = evidence(cli_runner, record)
    assert record["status"] == "in-progress"
    assert transition(cli_runner, record, "verified")["status"] == "verified"


def test_semantic_and_manual_edits_stale_evidence_without_read_writes(
    workspace, cli_runner
):
    record = verify(cli_runner, setup_requirement(cli_runner))
    identity = record["id"]
    path = workspace.roadmap_dir / f"requirements/{identity}.md"
    command(cli_runner, "update", identity, "--owner", "Carol")
    command(cli_runner, "rekey", identity, "--key", "UR-012")
    same = command(cli_runner, "view", identity)["requirement"]
    assert same["status"] == "verified" and same["evidence"] == record["evidence"]
    header, _body = path.read_text().rsplit("\n---\n", 1)
    path.write_text(header + "\n---\nManual change\n")
    before = canonical(workspace)
    stale = command(cli_runner, "view", identity)["requirement"]
    assert stale["status"] == "draft" and stale["recorded_status"] == "verified"
    assert not stale["acceptance_current"]
    assert stale["verification"] == {"C1": "missing", "C2": "missing"}
    assert command(cli_runner, "list", "--status", "verified")["requirements"] == []
    assert command(cli_runner, "list", "--status", "draft")["requirements"] == [stale]
    assert canonical(workspace) == before
    run(cli_runner, "health", "fix", "--fix-type", "projection", "--yes")
    assert canonical(workspace) == before
    database = workspace.roadmap_dir / "db/projection.db"
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT status FROM documents WHERE entity_id = ?", (identity,)
        ).fetchone() == ("draft",)
    renewed = transition(cli_runner, stale, "accepted")
    assert renewed["evidence"] == record["evidence"]
    assert len(renewed["acceptances"]) == 2 and len(renewed["revisions"]) == 3
    assert renewed["verification"] == {"C1": "missing", "C2": "missing"}
    edited = command(cli_runner, "update", identity, "--scope", "New scope")[
        "requirement"
    ]
    assert edited["status"] == "draft" and edited["active_acceptance_id"] is None
    assert edited["evidence"] == record["evidence"]


def test_reacceptance_and_withdrawal_do_not_reuse_old_proof(workspace, cli_runner):
    record = verify(cli_runner, setup_requirement(cli_runner))
    renewed = transition(cli_runner, record, "accepted")
    assert renewed["current_revision"] == record["current_revision"]
    assert renewed["active_acceptance_id"] != record["active_acceptance_id"]
    assert renewed["verification"] == {"C1": "missing", "C2": "missing"}
    deferred = transition(cli_runner, renewed, "deferred")
    assert deferred["active_acceptance_id"] is None
    draft = transition(cli_runner, deferred, "draft")
    rejected = transition(cli_runner, draft, "rejected")
    assert rejected["status"] == "rejected"
    assert rejected["evidence"] == record["evidence"]


def test_old_acceptance_and_stale_intent_results_refuse_atomically(
    workspace, cli_runner
):
    record = verify(cli_runner, setup_requirement(cli_runner))
    renewed = transition(cli_runner, record, "accepted")
    before = canonical(workspace)
    failed = cli_runner.invoke(
        cli,
        [
            "requirement",
            "evidence",
            record["id"],
            "--criterion",
            "C1",
            "--result",
            "pass",
            "--reference",
            "commit:old-cycle",
            "--expected-revision",
            record["current_revision"],
            "--acceptance-id",
            record["active_acceptance_id"],
        ],
    )
    assert failed.exit_code == 1 and "acceptance changed" in failed.stderr
    assert canonical(workspace) == before
    command(cli_runner, "update", record["id"], "--scope", "Changed scope")
    before = canonical(workspace)
    failed = cli_runner.invoke(
        cli,
        [
            "requirement",
            "evidence",
            record["id"],
            "--criterion",
            "C1",
            "--result",
            "pass",
            "--reference",
            "commit:old-intent",
            "--expected-revision",
            record["current_revision"],
            "--acceptance-id",
            renewed["active_acceptance_id"],
        ],
    )
    assert failed.exit_code == 1 and "intent changed" in failed.stderr
    assert canonical(workspace) == before


def test_observed_manual_change_cannot_restore_acceptance_by_reverting(
    workspace, cli_runner
):
    record = verify(cli_runner, setup_requirement(cli_runner))
    path = workspace.roadmap_dir / f"requirements/{record['id']}.md"
    header, _body = path.read_text().rsplit("\n---\n", 1)
    path.write_text(header + "\n---\nManual change\n")
    changed = command(
        cli_runner,
        "update",
        record["id"],
        "--statement",
        record["definition"]["statement"],
    )["requirement"]
    assert changed["current_revision"] == record["current_revision"]
    assert changed["status"] == "draft" and changed["active_acceptance_id"] is None
    assert changed["evidence"] == record["evidence"]


def test_governance_external_edit_and_issue_close_preserve_requirement(
    workspace, cli_runner, monkeypatch
):
    record = transition(cli_runner, setup_requirement(cli_runner), "accepted")
    before = canonical(workspace)
    issue = run(
        cli_runner, "issue", "create", "--title", "Implementation work", "--print-id"
    ).stdout.strip()
    run(cli_runner, "issue", "close", issue, "--reason", "Work complete")
    assert command(cli_runner, "view", record["id"])["requirement"] == record
    path = workspace.roadmap_dir / f"requirements/{record['id']}.md"
    assert path.read_bytes() == before[path]
    original = CanonicalUnitOfWork.save_requirement

    def racing_save(unit, requirement):
        original(unit, requirement)
        path.write_text(path.read_text() + "\nExternal governance edit survives\n")

    monkeypatch.setattr(CanonicalUnitOfWork, "save_requirement", racing_save)
    failed = cli_runner.invoke(
        cli,
        [
            "requirement",
            "evidence",
            record["id"],
            "--criterion",
            "C1",
            "--result",
            "pass",
            "--reference",
            "commit:race",
            "--expected-revision",
            record["current_revision"],
            "--acceptance-id",
            record["active_acceptance_id"],
        ],
    )
    assert failed.exit_code == 1
    assert "External governance edit survives" in path.read_text()
    current = command(cli_runner, "view", record["id"])["requirement"]
    assert current["evidence"] == [] and current["status"] == "draft"


def test_invalid_or_stale_governance_refuses_without_canonical_mutation(
    workspace, cli_runner
):
    record = setup_requirement(cli_runner)
    revision = record["current_revision"]
    base = ["--expected-revision", revision]
    failures = [
        [
            "evidence",
            record["id"],
            *base,
            "--criterion",
            "C1",
            "--result",
            "pass",
            "--reference",
            "sha",
        ],
        [
            "transition",
            record["id"],
            *base,
            "--status",
            "in-progress",
            "--reason",
            "Skip",
        ],
        ["transition", record["id"], *base, "--status", "accepted", "--reason", " "],
        [
            "transition",
            record["id"],
            "--expected-revision",
            "wrong",
            "--status",
            "accepted",
            "--reason",
            "Reviewed",
        ],
    ]
    before = canonical(workspace)
    for args in failures:
        assert cli_runner.invoke(cli, ["requirement", *args]).exit_code != 0
        assert canonical(workspace) == before
    accepted = transition(cli_runner, record, "accepted")
    before = canonical(workspace)
    for criterion, reference, result in [
        ("unknown", "sha", "pass"),
        ("C1", " ", "pass"),
        ("C1", "sha", "invalid"),
    ]:
        failed = cli_runner.invoke(
            cli,
            [
                "requirement",
                "evidence",
                record["id"],
                *base,
                "--criterion",
                criterion,
                "--reference",
                reference,
                "--result",
                result,
                "--acceptance-id",
                accepted["active_acceptance_id"],
            ],
        )
        assert failed.exit_code != 0
        assert canonical(workspace) == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "verified"),
        ("active_acceptance_id", "unknown"),
        ("evidence", [{}]),
        ("evidence", {}),
        ("acceptances", {}),
    ],
)
def test_malformed_governance_is_diagnosed_without_rewrite(
    workspace, cli_runner, field, value
):
    record = setup_requirement(cli_runner)
    path = workspace.roadmap_dir / f"requirements/{record['id']}.md"
    _, frontmatter, body = path.read_text().split("---", 2)
    data = yaml.safe_load(frontmatter)
    data[field] = value
    path.write_text("---\n" + yaml.safe_dump(data) + "---" + body)
    before = canonical(workspace)
    failed = cli_runner.invoke(cli, ["requirement", "view", record["id"]])
    assert failed.exit_code == 1 and "requirement" in failed.stderr
    assert canonical(workspace) == before


@pytest.mark.parametrize("stage", ["before_validate", "after_replace"])
def test_governance_transaction_recovery_preserves_history(
    workspace, cli_runner, monkeypatch, stage
):
    record = transition(cli_runner, setup_requirement(cli_runner), "accepted")
    original_commit = CanonicalUnitOfWork.commit

    def fail(current, _path):
        if current == stage:
            raise OSError("injected governance transaction failure")

    def commit(unit):
        unit._inject = fail
        return original_commit(unit)

    with monkeypatch.context() as patch:
        patch.setattr(CanonicalUnitOfWork, "commit", commit)
        failed = cli_runner.invoke(
            cli,
            [
                "requirement",
                "evidence",
                record["id"],
                "--criterion",
                "C1",
                "--result",
                "pass",
                "--reference",
                "commit:retry",
                "--expected-revision",
                record["current_revision"],
                "--acceptance-id",
                record["active_acceptance_id"],
            ],
        )
        assert failed.exit_code == 1
    recovered = command(cli_runner, "view", record["id"])["requirement"]
    if not recovered["evidence"]:
        recovered = evidence(cli_runner, recovered)
    assert len(recovered["evidence"]) == 1
    assert recovered["history"][: len(record["history"])] == record["history"]
    assert recovered["active_acceptance_id"] == record["active_acceptance_id"]
