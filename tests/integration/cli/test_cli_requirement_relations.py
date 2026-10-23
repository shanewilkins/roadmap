"""Canonical typed traceability, reverse discovery and atomic refusals."""

import json

import yaml

from roadmap.adapters.outbound.persistence.canonical import CanonicalUnitOfWork
from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
from roadmap.bootstrap import cli
from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.types import (
    EntityId,
    IssueStatus,
    MilestoneStatus,
    Name,
    ProjectStatus,
    RetentionState,
    Title,
)
from tests.fixtures.cli_workspace import NOW, run, seed
from tests.integration.cli.test_cli_requirements import (
    canonical,
    command,
    create,
    enable,
)


def technical(runner):
    return command(
        runner,
        "create",
        "--type",
        "technical",
        "--title",
        "Implement intent",
        "--statement",
        "Implementation contract",
        "--criterion",
        "C1=Trace work",
    )["requirement"]


def link(runner, record, relation, target):
    return command(
        runner,
        "link",
        record["id"],
        "--relation",
        relation,
        "--target",
        target,
    )["requirement"]


def test_all_relation_types_reverse_filter_and_projection_rebuild(
    workspace, cli_runner
):
    enable(cli_runner)
    user = create(cli_runner)
    implementation = technical(cli_runner)
    original_revision = user["current_revision"]
    issue_id = EntityId("00000000-0000-4000-8000-000000000101")
    milestone_id = EntityId("00000000-0000-4000-8000-000000000102")
    project_id = EntityId("00000000-0000-4000-8000-000000000103")
    issue = Issue(
        issue_id,
        NOW,
        NOW,
        title=Title("Closed implementation"),
        status=IssueStatus.CLOSED,
        retention=RetentionState.ARCHIVED,
    )
    milestone = Milestone(
        milestone_id,
        NOW,
        NOW,
        name=Name("Release"),
        status=MilestoneStatus.CLOSED,
        retention=RetentionState.ARCHIVED,
    )
    project = Project(
        project_id,
        NOW,
        NOW,
        name=Name("Product"),
        status=ProjectStatus.COMPLETED,
        retention=RetentionState.ARCHIVED,
    )
    seed(workspace, issue, milestone, project)

    implementation = link(cli_runner, implementation, "supports", user["key"])
    user = link(cli_runner, user, "depends-on", implementation["key"])
    user = link(cli_runner, user, "implemented-by", str(issue_id))
    user = link(cli_runner, user, "project-target", str(project_id))
    user = link(cli_runner, user, "milestone-target", str(milestone_id))
    user = link(
        cli_runner,
        user,
        "report",
        "https://github.com/acme/widgets/issues/42",
    )

    assert user["current_revision"] == original_revision
    assert user["relations"]["implemented_by"] == [str(issue_id)]
    assert user["relations"]["project_target"] == str(project_id)
    assert user["relations"]["milestone_target"] == str(milestone_id)
    assert user["relations"]["reports"][0]["actor"]
    assert command(cli_runner, "list", "--relation", f"implemented-by={issue_id}")[
        "requirements"
    ] == [user]
    assert command(cli_runner, "list", "--relation", f"supports={user['key']}")[
        "requirements"
    ] == [implementation]

    run(cli_runner, "health", "fix", "--fix-type", "projection", "--yes")
    repository = DocumentRepository(workspace.roadmap_dir)
    projection = SQLiteProjection(
        workspace.roadmap_dir / "db/projection.db", repository
    )
    assert projection.requirement_sources("implemented-by", str(issue_id)) == (
        user["id"],
    )
    assert projection.requirement_sources("supports", user["id"]) == (
        implementation["id"],
    )

    before_issue = repository.load("issue", issue_id)
    unlinked = command(
        cli_runner,
        "unlink",
        user["id"],
        "--relation",
        "implemented-by",
        "--target",
        str(issue_id),
    )["requirement"]
    assert unlinked["relations"]["implemented_by"] == []
    assert repository.load("issue", issue_id) == before_issue


def test_invalid_types_missing_targets_duplicates_and_cycles_refuse_atomically(
    workspace, cli_runner
):
    enable(cli_runner)
    user = create(cli_runner)
    implementation = technical(cli_runner)
    before = canonical(workspace)
    failures = [
        ["link", user["id"], "--relation", "supports", "--target", user["id"]],
        [
            "link",
            user["id"],
            "--relation",
            "implemented-by",
            "--target",
            "missing",
        ],
        [
            "link",
            user["id"],
            "--relation",
            "project-target",
            "--target",
            "missing",
        ],
    ]
    for arguments in failures:
        assert cli_runner.invoke(cli, ["requirement", *arguments]).exit_code == 1
        assert canonical(workspace) == before

    user = link(cli_runner, user, "depends-on", implementation["id"])
    before = canonical(workspace)
    failed = cli_runner.invoke(
        cli,
        [
            "requirement",
            "link",
            implementation["id"],
            "--relation",
            "depends-on",
            "--target",
            user["id"],
        ],
    )
    assert failed.exit_code == 1 and "cycle" in failed.stderr
    assert canonical(workspace) == before
    link(cli_runner, user, "implemented-by", seed_issue(workspace))
    before = canonical(workspace)
    duplicate = cli_runner.invoke(
        cli,
        [
            "requirement",
            "link",
            user["id"],
            "--relation",
            "implemented-by",
            "--target",
            seed_issue(workspace),
        ],
    )
    assert duplicate.exit_code == 1
    assert canonical(workspace) == before


def seed_issue(workspace):
    identity = EntityId("00000000-0000-4000-8000-000000000201")
    repository = DocumentRepository(workspace.roadmap_dir)
    if repository.load("issue", identity) is None:
        seed(workspace, Issue(identity, NOW, NOW, title=Title("Work")))
    return str(identity)


def test_manual_broken_requirement_relation_is_diagnosed_without_rewrite(
    workspace, cli_runner
):
    enable(cli_runner)
    record = create(cli_runner)
    path = workspace.roadmap_dir / f"requirements/{record['id']}.md"
    frontmatter, body = path.read_text().removeprefix("---\n").split("---\n", 1)
    data = yaml.safe_load(frontmatter)
    data["relations"]["implemented_by"] = ["missing-issue"]
    path.write_text("---\n" + yaml.safe_dump(data, sort_keys=False) + "---\n" + body)
    before = path.read_bytes()
    report = json.loads(
        run(cli_runner, "health", "scan", "--format", "json", code=2).stdout
    )
    findings = report["findings"]
    assert any(
        item["finding_id"] == "canonical.broken-reference"
        and item["entity_id"] == record["id"]
        for item in findings
    )
    assert path.read_bytes() == before
    repaired = command(
        cli_runner,
        "unlink",
        record["id"],
        "--relation",
        "implemented-by",
        "--target",
        "missing-issue",
    )["requirement"]
    assert repaired["relations"]["implemented_by"] == []


def test_external_edit_during_relation_write_is_preserved(
    workspace, cli_runner, monkeypatch
):
    enable(cli_runner)
    record = create(cli_runner)
    issue_id = seed_issue(workspace)
    path = workspace.roadmap_dir / f"requirements/{record['id']}.md"
    original = CanonicalUnitOfWork.save_requirement

    def racing_save(unit, requirement):
        original(unit, requirement)
        path.write_text(path.read_text() + "\nExternal relation edit survives\n")

    monkeypatch.setattr(CanonicalUnitOfWork, "save_requirement", racing_save)
    failed = cli_runner.invoke(
        cli,
        [
            "requirement",
            "link",
            record["id"],
            "--relation",
            "implemented-by",
            "--target",
            issue_id,
        ],
    )
    assert failed.exit_code == 1
    assert "External relation edit survives" in path.read_text()
    assert (
        command(cli_runner, "view", record["id"])["requirement"]["relations"][
            "implemented_by"
        ]
        == []
    )
