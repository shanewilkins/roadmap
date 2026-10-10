"""Real-storage import identity, immutable source revisions and safe retries."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from roadmap.adapters.outbound.github.issues import GhIssueSource
from roadmap.adapters.outbound.persistence.canonical import (
    CanonicalIssueUnitOfWorkFactory,
    CanonicalUnitOfWork,
)
from roadmap.application.use_cases.github_import import (
    captured_sources,
    validate_source,
)
from roadmap.bootstrap import cli
from tests.fixtures.cli_workspace import canonical_bytes, run, seed
from tests.integration.cli.test_cli_mutation_contracts import entity, load


def payload(
    number=1,
    *,
    repository="owner/repo",
    title="Reported issue",
    body="Full Markdown\n\n**context**",
    state="open",
    comments=None,
):
    comments = comments or []
    return {
        "issue": {
            "number": number,
            "node_id": f"issue-{number}",
            "html_url": f"https://github.com/{repository}/issues/{number}",
            "title": title,
            "body": body,
            "state": state,
            "comments": len(comments),
            "user": {"login": "reporter"},
            "created_at": "2026-10-10T00:00:00Z",
            "updated_at": "2026-10-10T00:00:00Z",
            "labels": [],
            "assignees": [],
            "milestone": None,
        },
        "comments": comments,
        "timeline": [],
    }


@pytest.fixture
def sources(monkeypatch):
    values = {1: payload(), 2: payload(2)}

    def fetch(_self, repository, numbers):
        return tuple(
            validate_source(repository, number, values[number]) for number in numbers
        )

    monkeypatch.setattr(GhIssueSource, "fetch", fetch)
    return values


def import_result(runner, *numbers, apply=False, repository="owner/repo"):
    arguments = ["github", "import", "--repo", repository, *map(str, numbers)]
    if apply:
        arguments.append("--apply")
    return json.loads(run(runner, *arguments).stdout)["issues"]


def test_preview_apply_repeat_and_revision_preserve_local_planning(
    workspace, cli_runner, sources
):
    before = canonical_bytes(workspace)
    preview = import_result(cli_runner, 1)
    assert preview[0]["action"] == "create" and preview[0]["issue_id"] is None
    assert canonical_bytes(workspace) == before
    [created] = import_result(cli_runner, 1, apply=True)
    identity = created["issue_id"]
    run(
        cli_runner,
        "issue",
        "update",
        identity,
        "--title",
        "Local plan",
        "--assignee",
        "Alice",
        "--description",
        "Local context",
        "--add-label",
        "maintenance",
    )
    run(cli_runner, "issue", "comment", "add", identity, "Local decision")
    run(cli_runner, "issue", "close", identity, "--reason", "Local disposition")
    local = load(workspace, "issue", identity)
    before = canonical_bytes(workspace)
    assert import_result(cli_runner, 1, apply=True)[0]["action"] == "unchanged"
    assert canonical_bytes(workspace) == before
    sources[1] = payload(
        title="Changed upstream title", body="Changed source only", state="closed"
    )
    assert import_result(cli_runner, 1, apply=True)[0]["issue_id"] == identity
    updated = load(workspace, "issue", identity)
    assert (
        updated.title,
        updated.content,
        updated.status,
        updated.assignee,
        updated.labels,
        updated.relations,
    ) == (
        local.title,
        local.content,
        local.status,
        local.assignee,
        local.labels,
        local.relations,
    )
    assert updated.comments[:-1] == local.comments
    assert updated.history[:-1] == local.history
    assert len(captured_sources(updated)) == 2
    before = canonical_bytes(workspace)
    sources[1] = payload()
    assert import_result(cli_runner, 1, apply=True)[0]["action"] == "reuse-revision"
    assert canonical_bytes(workspace) == before


@pytest.mark.parametrize("archived", [False, True])
def test_legacy_closed_and_archived_source_records_reuse_ids(
    workspace, cli_runner, sources, archived
):
    value = replace(
        entity("issue", "existing", closed=True, archived=archived),
        labels=("github:1",),
        content="Baseline GitHub report: https://github.com/owner/repo/issues/1\nLocal rationale",
    )
    seed(workspace, value)
    [result] = import_result(cli_runner, 1, apply=True)
    assert result["issue_id"] == "existing"
    imported = load(workspace, "issue", "existing")
    assert imported.status == value.status and imported.retention == value.retention
    assert imported.content == value.content
    before = canonical_bytes(workspace)
    import_result(cli_runner, 1, apply=True)
    assert canonical_bytes(workspace) == before


def test_qualified_repository_identity_never_matches_bare_number_or_title(
    workspace, cli_runner, sources
):
    seed(
        workspace,
        replace(entity("issue", "bare"), labels=("github:1",)),
        replace(
            entity("issue", "other"),
            content="Baseline GitHub report: https://github.com/other/repo/issues/1",
        ),
    )
    before = canonical_bytes(workspace)
    refusal = cli_runner.invoke(
        cli, ["github", "import", "--repo", "owner/repo", "1", "--apply"]
    )
    assert refusal.exit_code == 1 and "unqualified legacy" in refusal.stderr
    assert canonical_bytes(workspace) == before
    run(
        cli_runner,
        "issue",
        "update",
        "bare",
        "--add-label",
        "github-source:owner/repo#1",
    )
    [result] = import_result(cli_runner, 1, apply=True)
    assert result["issue_id"] == "bare"


def test_duplicate_local_identity_refuses_entire_batch_without_mutation(
    workspace, cli_runner, sources
):
    for identity in ["a", "b"]:
        seed(
            workspace,
            replace(
                entity("issue", identity),
                content="Baseline GitHub report: https://github.com/owner/repo/issues/1",
            ),
        )
    before = canonical_bytes(workspace)
    result = cli_runner.invoke(
        cli, ["github", "import", "--repo", "owner/repo", "2", "1", "--apply"]
    )
    assert result.exit_code == 1 and "Duplicate local records" in result.stderr
    assert canonical_bytes(workspace) == before


def test_changed_node_identity_and_edited_provenance_refuse_import(
    workspace, cli_runner, sources
):
    [result] = import_result(cli_runner, 1, apply=True)
    before = canonical_bytes(workspace)
    sources[1]["issue"]["node_id"] = "different-node"
    refusal = cli_runner.invoke(
        cli, ["github", "import", "--repo", "owner/repo", "1", "--apply"]
    )
    assert refusal.exit_code == 1 and "node identity" in refusal.stderr
    assert canonical_bytes(workspace) == before
    sources[1] = payload()
    path = workspace.roadmap_dir / "issues" / f"{result['issue_id']}.md"
    path.write_text(path.read_text().replace("Reported issue", "Edited source"))
    before = canonical_bytes(workspace)
    refusal = cli_runner.invoke(
        cli, ["github", "import", "--repo", "owner/repo", "1", "--apply"]
    )
    assert refusal.exit_code == 1 and "provenance was edited" in refusal.stderr
    assert canonical_bytes(workspace) == before


def test_apply_rechecks_matching_after_preview_and_comments_stay_in_source(
    workspace, cli_runner, sources
):
    sources[1] = payload(
        comments=[
            {
                "id": 9,
                "body": "Original author text",
                "user": {"login": "contributor"},
                "created_at": "2026-10-10T00:00:00Z",
                "updated_at": "2026-10-10T00:00:00Z",
                "html_url": "https://github.com/owner/repo/issues/1#issuecomment-9",
            }
        ]
    )
    assert import_result(cli_runner, 1)[0]["action"] == "create"
    seed(
        workspace,
        replace(entity("issue", "concurrent"), labels=("github-publish:owner/repo#1",)),
    )
    assert import_result(cli_runner, 1, apply=True)[0]["issue_id"] == "concurrent"
    value = load(workspace, "issue", "concurrent")
    assert len(value.comments) == 1
    source = json.loads(captured_sources(value)[0].payload)
    assert source["comments"][0]["user"]["login"] == "contributor"
    assert source["comments"][0]["body"] == "Original author text"


@pytest.mark.parametrize("numbers", [[], ["1", "1"], ["0"]])
def test_invalid_selection_does_not_fetch_or_mutate(
    workspace, cli_runner, monkeypatch, numbers
):
    monkeypatch.setattr(
        GhIssueSource,
        "fetch",
        lambda *_: pytest.fail("invalid selection must not fetch"),
    )
    before = canonical_bytes(workspace)
    result = cli_runner.invoke(
        cli, ["github", "import", "--repo", "owner/repo", *numbers, "--apply"]
    )
    assert result.exit_code != 0
    assert canonical_bytes(workspace) == before


def test_concurrent_applies_create_one_identity_and_one_source_revision(
    workspace, sources
):
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(workspace.github_import.execute, "owner/repo", (1,), apply=True)
            for _ in range(2)
        ]
        results = [future.result(timeout=20)[0] for future in futures]
    assert {item.action for item in results} == {"create", "unchanged"}
    assert len({item.issue_id for item in results}) == 1
    identity = results[0].issue_id
    assert len(captured_sources(load(workspace, "issue", identity))) == 1


@pytest.mark.parametrize("stage", ["before_validate", "after_replace"])
def test_failed_transaction_retries_without_duplicate_records(
    workspace, cli_runner, sources, monkeypatch, stage
):
    def fail(current, _path):
        if current == stage:
            raise OSError("injected import transaction failure")

    def failing(factory, *, read_only=False):
        return CanonicalUnitOfWork(
            factory._repository,
            factory._projection,
            read_only=read_only,
            failure_injector=fail,
        )

    with monkeypatch.context() as patch:
        patch.setattr(CanonicalIssueUnitOfWorkFactory, "create", failing)
        failure = cli_runner.invoke(
            cli, ["github", "import", "--repo", "owner/repo", "1", "2", "--apply"]
        )
        assert failure.exit_code == 1
    results = import_result(cli_runner, 1, 2, apply=True)
    assert len({item["issue_id"] for item in results}) == 2
    before = canonical_bytes(workspace)
    assert all(
        item["action"] == "unchanged"
        for item in import_result(cli_runner, 1, 2, apply=True)
    )
    assert canonical_bytes(workspace) == before
    assert len(list((workspace.roadmap_dir / "issues").glob("*.md"))) == 2


def test_incomplete_extraction_and_pr_targets_fail_without_mutation(
    workspace, cli_runner, monkeypatch
):
    before = canonical_bytes(workspace)
    monkeypatch.setattr(GhIssueSource, "fetch", lambda *_: ())
    failure = cli_runner.invoke(
        cli, ["github", "import", "--repo", "owner/repo", "1", "--apply"]
    )
    assert failure.exit_code == 1 and "exactly the selected" in failure.stderr
    assert canonical_bytes(workspace) == before

    value = payload()
    value["issue"]["pull_request"] = {}
    monkeypatch.setattr(
        GhIssueSource, "fetch", lambda *_: (validate_source("owner/repo", 1, value),)
    )
    failure = cli_runner.invoke(
        cli, ["github", "import", "--repo", "owner/repo", "1", "--apply"]
    )
    assert failure.exit_code == 1
    assert canonical_bytes(workspace) == before


def test_explicit_duplicate_owner_preserves_history_and_reuses_original(
    workspace, cli_runner, sources
):
    seed(
        workspace,
        replace(
            entity("issue", "original", closed=True),
            labels=("github-source:owner/repo#1",),
        ),
    )
    duplicate = replace(
        entity("issue", "duplicate", closed=True),
        labels=(
            "github-source:owner/repo#1",
            "resolution:duplicate",
            "github-source-owner:original",
        ),
    )
    seed(workspace, duplicate)
    path = workspace.roadmap_dir / "issues/duplicate.md"
    before = path.read_bytes()
    assert import_result(cli_runner, 1, apply=True)[0]["issue_id"] == "original"
    assert path.read_bytes() == before
    run(
        cli_runner,
        "issue",
        "update",
        "duplicate",
        "--remove-label",
        "github-source-owner:original",
        "--add-label",
        "github-source-owner:missing",
    )
    before = canonical_bytes(workspace)
    failed = cli_runner.invoke(
        cli, ["github", "import", "--repo", "owner/repo", "1", "--apply"]
    )
    assert failed.exit_code == 1 and "Invalid source-owner" in failed.stderr
    assert canonical_bytes(workspace) == before


def test_transferred_node_refuses_creation_under_another_target(
    workspace, cli_runner, sources
):
    import_result(cli_runner, 1, apply=True)
    sources[2]["issue"]["node_id"] = "issue-1"
    before = canonical_bytes(workspace)
    failure = cli_runner.invoke(
        cli, ["github", "import", "--repo", "owner/repo", "2", "--apply"]
    )
    assert failure.exit_code == 1 and "transfer/rename" in failure.stderr
    assert canonical_bytes(workspace) == before


def test_projection_failure_warns_and_retry_does_not_duplicate_capture(
    workspace, cli_runner, sources, monkeypatch
):
    from roadmap.adapters.outbound.persistence.projection import SQLiteProjection

    def fail(*_args, **_kwargs):
        raise OSError("projection unavailable")

    with monkeypatch.context() as patch:
        patch.setattr(SQLiteProjection, "refresh", fail)
        result = run(
            cli_runner, "github", "import", "--repo", "owner/repo", "1", "--apply"
        )
    assert "canonical Markdown was saved" in result.stderr
    assert json.loads(result.stdout)["issues"][0]["projection_stale"] is True
    before = canonical_bytes(workspace)
    assert import_result(cli_runner, 1, apply=True)[0]["action"] == "unchanged"
    assert canonical_bytes(workspace) == before
