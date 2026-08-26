#!/usr/bin/env python3
"""Run retained Roadmap journeys without touching the source workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = REPOSITORY_ROOT / "tests" / "fixtures" / "compatibility" / "v0_1_1"


def validate_workspace(workspace: Path) -> Path:
    """Accept only a dedicated child of the platform temporary directory."""
    resolved = workspace.resolve()
    temporary_roots = {
        Path(tempfile.gettempdir()).resolve(),
        Path("/tmp").resolve(),
    }
    if not any(
        resolved != root and resolved.is_relative_to(root) for root in temporary_roots
    ):
        roots = ", ".join(str(root) for root in sorted(temporary_roots))
        raise ValueError(f"Workspace must be below a temporary root: {roots}")
    if resolved.is_relative_to(REPOSITORY_ROOT):
        raise ValueError("Workspace must not be inside the Roadmap repository")
    return resolved


def canonical_digests(workspace: Path) -> dict[str, str]:
    """Hash canonical project, milestone, and issue documents."""
    roadmap_dir = workspace / ".roadmap"
    files = []
    for pattern in (
        "projects/**/*.md",
        "archive/projects/**/*.md",
        "milestones/**/*.md",
        "archive/milestones/**/*.md",
        "issues/**/*.md",
        "archive/issues/**/*.md",
    ):
        files.extend(roadmap_dir.glob(pattern))
    return {
        str(path.relative_to(workspace)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(set(files))
    }


def verify_fixture_digests(fixture: Path) -> dict[str, str]:
    """Verify and return the tracked fixture's canonical digests."""
    expected = json.loads((fixture / "canonical-digests.json").read_text())
    actual = canonical_digests(fixture)
    if actual != expected:
        raise RuntimeError("Compatibility fixture canonical digests do not match")
    return actual


def _clean_environment(overrides: dict[str, str] | None = None) -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment.update(overrides or {})
    return environment


def _run(
    command: list[str],
    workspace: Path,
    *,
    parse_json: bool = False,
    environment: dict[str, str] | None = None,
) -> str | Any:
    print(f"+ {' '.join(command)}", flush=True)
    result = subprocess.run(
        command,
        cwd=workspace,
        env=_clean_environment(environment),
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    if parse_json:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            for index, character in enumerate(output):
                if character not in "[{":
                    continue
                try:
                    value, end = decoder.raw_decode(output[index:])
                except json.JSONDecodeError:
                    continue
                if not output[index + end :].strip():
                    return value
            raise
    return output


def _materialize_fixture(fixture: Path, workspace: Path) -> None:
    shutil.copytree(fixture / ".roadmap", workspace / ".roadmap")
    database = workspace / ".roadmap" / "db" / "state.db"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.executescript((fixture / "projection.sql").read_text())


def _workspace_digests(workspace: Path) -> dict[str, str]:
    """Hash every workspace file so a migration dry run proves non-mutation."""
    return {
        str(path.relative_to(workspace)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(workspace.rglob("*"))
        if path.is_file()
    }


def inspect_fixture(roadmap: Path, fixture: Path, workspace: Path) -> dict[str, Any]:
    """Migrate the compatibility fixture and return a semantic snapshot."""
    verify_fixture_digests(fixture)
    _materialize_fixture(fixture, workspace)
    expected = json.loads((fixture / "expected.json").read_text())
    home = workspace.parent / f"{workspace.name}-home"
    home.mkdir()
    environment = {"HOME": str(home)}

    before_dry_run = _workspace_digests(workspace)
    dry_run = _run(
        [str(roadmap), "migrate", "--dry-run", "--format", "json"],
        workspace,
        parse_json=True,
        environment=environment,
    )
    if not dry_run["required"] or dry_run["conflicts"]:
        raise RuntimeError("Compatibility fixture migration preflight was invalid")
    if _workspace_digests(workspace) != before_dry_run or any(home.rglob("*")):
        raise RuntimeError("Migration dry run changed workspace or user files")

    migrated = _run(
        [str(roadmap), "migrate", "--yes", "--format", "json"],
        workspace,
        parse_json=True,
        environment=environment,
    )
    if migrated["status"] != "migrated" or not migrated["projection_rebuilt"]:
        raise RuntimeError("Compatibility fixture migration did not complete")

    roadmap_dir = workspace / ".roadmap"
    expected_paths = {
        roadmap_dir / "projects" / f"{expected['project_id']}.md",
        roadmap_dir / "milestones" / f"{expected['milestone']}.md",
        roadmap_dir / "issues" / f"{expected['visible_issue_id']}.md",
        roadmap_dir / "issues" / f"{expected['closed_issue_id']}.md",
        roadmap_dir / "issues" / f"{expected['archived_issue_id']}.md",
    }
    if not all(path.is_file() for path in expected_paths):
        raise RuntimeError("Migration did not produce stable flat canonical paths")
    config = (roadmap_dir / "config.yaml").read_text()
    if "workspace_schema_version: 1" not in config:
        raise RuntimeError("Migration did not write the workspace schema marker")
    user_config = home / ".config" / "roadmap" / "config.yaml"
    if not user_config.is_file():
        raise RuntimeError("Migration did not externalize user preferences")

    projects = _run(
        [str(roadmap), "project", "list"], workspace, environment=environment
    )
    milestones = _run(
        [str(roadmap), "milestone", "list"], workspace, environment=environment
    )
    issues = _run(
        [str(roadmap), "issue", "list", "--format", "json"],
        workspace,
        parse_json=True,
        environment=environment,
    )
    comments = _run(
        [
            str(roadmap),
            "issue",
            "comment",
            "list",
            expected["visible_issue_id"],
            "--format",
            "json",
        ],
        workspace,
        parse_json=True,
        environment=environment,
    )
    closed_issue = _run(
        [str(roadmap), "issue", "view", expected["closed_issue_id"]],
        workspace,
        environment=environment,
    )
    archived = _run(
        [str(roadmap), "issue", "archive", "--list"],
        workspace,
        environment=environment,
    )

    visible_ids = sorted(row[0] for row in issues["rows"])
    snapshot = {
        "archived_visible": expected["archived_issue_id"] in archived,
        "closed_issue_visible": expected["closed_issue_id"] in closed_issue,
        "comment_bodies": [comment["body"] for comment in comments],
        "milestone_visible": expected["milestone"] in milestones,
        "project_visible": expected["project_id"] in projects,
        "visible_issue_ids": visible_ids,
    }
    if expected["visible_issue_id"] not in visible_ids:
        raise RuntimeError("Compatibility fixture issues were not loaded")
    if snapshot["comment_bodies"] != [expected["comment_body"]]:
        raise RuntimeError("Compatibility fixture comment changed semantically")
    if not all(
        snapshot[key]
        for key in (
            "archived_visible",
            "closed_issue_visible",
            "milestone_visible",
            "project_visible",
        )
    ):
        raise RuntimeError("Compatibility fixture relationship was not visible")

    before_rebuild = canonical_digests(workspace)
    projection_path = workspace / ".roadmap" / "db" / "projection.db"
    projection_path.write_bytes(b"deliberately corrupt projection")
    repair = _run(
        [str(roadmap), "migrate", "--yes", "--format", "json"],
        workspace,
        parse_json=True,
        environment=environment,
    )
    if not repair["projection_rebuilt"]:
        raise RuntimeError("Compatibility fixture projection rebuild failed")
    if canonical_digests(workspace) != before_rebuild:
        raise RuntimeError("Fixture projection rebuild changed canonical documents")
    with sqlite3.connect(projection_path) as connection:
        projected = dict(
            connection.execute(
                "SELECT entity_id, retention FROM documents WHERE kind = 'issue'"
            )
        )
    expected_projection = {
        expected["visible_issue_id"]: "visible",
        expected["closed_issue_id"]: "visible",
        expected["archived_issue_id"]: "archived",
    }
    if projected != expected_projection:
        raise RuntimeError("Fixture projection rebuild was not semantically equivalent")
    repeated = _run(
        [str(roadmap), "migrate", "--yes", "--format", "json"],
        workspace,
        parse_json=True,
        environment=environment,
    )
    if repeated["required"]:
        raise RuntimeError("Repeated migration was not idempotent")
    return snapshot


def _extract_created_issue_id(output: str) -> str:
    match = re.search(
        r"(?:\bID:\s*|Created issue:\s*\[)([0-9a-f]{8}(?:-[0-9a-f-]{27})?)",
        output,
    )
    if not match:
        raise RuntimeError("Could not read the created issue ID")
    return match.group(1)


def run_fresh_journey(roadmap: Path, workspace: Path) -> None:
    """Exercise cumulative retained behavior in a new disposable workspace."""
    _run([str(roadmap), "--help"], workspace)
    _run([str(roadmap), "--version"], workspace)
    _run(
        [
            str(roadmap),
            "init",
            "--project-name",
            "Checkpoint Project",
            "--non-interactive",
        ],
        workspace,
    )
    _run(
        [str(roadmap), "config", "set", "identity.name", "checkpoint-user"],
        workspace,
    )
    projects = _run(
        [str(roadmap), "project", "list", "--format", "json"],
        workspace,
        parse_json=True,
    )
    if len(projects["rows"]) != 1:
        raise RuntimeError("Fresh project was not represented in structured output")
    project_id = projects["rows"][0][0]
    _run(
        [str(roadmap), "project", "update", project_id, "--status", "active"],
        workspace,
    )
    _run([str(roadmap), "project", "view", project_id], workspace)
    _run(
        [
            str(roadmap),
            "milestone",
            "create",
            "--title",
            "checkpoint-1",
            "--description",
            "Checkpoint milestone",
        ],
        workspace,
    )
    milestones = _run(
        [str(roadmap), "milestone", "list", "--format", "json"],
        workspace,
        parse_json=True,
    )
    if [row[0] for row in milestones["rows"]] != ["checkpoint-1"]:
        raise RuntimeError("Fresh milestone was not represented in structured output")
    _run([str(roadmap), "milestone", "view", "checkpoint-1"], workspace)
    create_output = _run(
        [
            str(roadmap),
            "issue",
            "create",
            "--title",
            "Checkpoint issue",
            "--milestone",
            "checkpoint-1",
        ],
        workspace,
    )
    issue_id = _extract_created_issue_id(create_output)
    _run([str(roadmap), "issue", "view", issue_id], workspace)
    _run([str(roadmap), "milestone", "kanban", "checkpoint-1"], workspace)
    _run([str(roadmap), "today"], workspace)
    _run(
        [
            str(roadmap),
            "issue",
            "comment",
            "add",
            issue_id,
            "Checkpoint comment",
            "--author",
            "fixture-user",
        ],
        workspace,
    )
    _run(
        [str(roadmap), "issue", "update", issue_id, "--status", "closed"],
        workspace,
    )
    _run([str(roadmap), "issue", "archive", issue_id, "--dry-run"], workspace)
    _run([str(roadmap), "issue", "archive", issue_id, "--force"], workspace)
    _run([str(roadmap), "issue", "restore", issue_id, "--force"], workspace)
    _run(
        [str(roadmap), "issue", "list", "--format", "json"],
        workspace,
        parse_json=True,
    )
    _run([str(roadmap), "milestone", "recalculate", "checkpoint-1"], workspace)
    _run([str(roadmap), "milestone", "close", "checkpoint-1"], workspace)
    _run(
        [str(roadmap), "milestone", "archive", "checkpoint-1", "--force"],
        workspace,
    )
    _run(
        [str(roadmap), "milestone", "restore", "checkpoint-1", "--force"],
        workspace,
    )
    _run([str(roadmap), "project", "close", project_id, "--force"], workspace)
    _run([str(roadmap), "project", "archive", project_id, "--force"], workspace)
    _run([str(roadmap), "project", "restore", project_id, "--force"], workspace)
    _run([str(roadmap), "status", "--format", "json"], workspace, parse_json=True)
    _run(
        [
            str(roadmap),
            "analysis",
            "critical-path",
            "--include-closed",
            "--export",
            "json",
        ],
        workspace,
        parse_json=True,
    )

    issue_file = next((workspace / ".roadmap" / "issues").rglob(f"{issue_id}*.md"))
    marker = "\nManual checkpoint edit observed.\n"
    issue_file.write_text(issue_file.read_text() + marker)
    if "Manual checkpoint edit observed" not in _run(
        [str(roadmap), "issue", "view", issue_id], workspace
    ):
        raise RuntimeError("Roadmap did not observe a manual canonical edit")

    exported = _run(
        [str(roadmap), "data", "export", "--format", "json"],
        workspace,
        parse_json=True,
    )
    if exported["kind"] != "roadmap.issue-export":
        raise RuntimeError("Canonical issue export schema was not available")

    before_rebuild = canonical_digests(workspace)
    preview = _run(
        [
            str(roadmap),
            "health",
            "fix",
            "--fix-type",
            "projection",
            "--dry-run",
            "--format",
            "json",
        ],
        workspace,
        parse_json=True,
    )
    if preview["mode"] != "dry-run":
        raise RuntimeError("Projection repair preview was not non-mutating")
    applied = _run(
        [
            str(roadmap),
            "health",
            "fix",
            "--fix-type",
            "projection",
            "--yes",
            "--format",
            "json",
        ],
        workspace,
        parse_json=True,
    )
    if applied["post_check"]["status"] != "healthy":
        raise RuntimeError("SQLite projection repair did not pass its post-check")
    if canonical_digests(workspace) != before_rebuild:
        raise RuntimeError("SQLite rebuild changed canonical documents")
    with sqlite3.connect(workspace / ".roadmap" / "db" / "projection.db") as connection:
        row = connection.execute(
            "SELECT entity_id FROM documents WHERE entity_id = ?", (issue_id,)
        ).fetchone()
    if row is None:
        raise RuntimeError("SQLite projection rebuild omitted the active issue")

    health = _run(
        [str(roadmap), "health", "--format", "json"],
        workspace,
        parse_json=True,
    )
    if health["kind"] != "roadmap.health" or health["status"] != "healthy":
        raise RuntimeError("Versioned health output did not report a clean workspace")
    _run(["git", "init"], workspace)
    _run([str(roadmap), "git", "status"], workspace)
    _run([str(roadmap), "git", "branch", issue_id, "--force"], workspace)
    linked = _run([str(roadmap), "git", "status"], workspace)
    if issue_id not in linked:
        raise RuntimeError("Local Git branch was not linked to the canonical issue")


def run_checkpoint(roadmap: Path, fixture: Path, workspace: Path) -> dict[str, Any]:
    """Run fresh and compatibility journeys below a validated workspace."""
    workspace = validate_workspace(workspace)
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError("Checkpoint workspace must be empty")
    workspace.mkdir(parents=True, exist_ok=True)
    checkpoint_home = workspace / "home"
    checkpoint_home.mkdir()
    os.environ["HOME"] = str(checkpoint_home)
    fresh = workspace / "fresh"
    compatibility = workspace / "compatibility"
    fresh.mkdir()
    compatibility.mkdir()
    run_fresh_journey(roadmap.resolve(strict=True), fresh)
    first = inspect_fixture(roadmap, fixture, compatibility)

    shutil.rmtree(compatibility)
    shutil.rmtree(workspace / "compatibility-home")
    compatibility.mkdir()
    second = inspect_fixture(roadmap, fixture, compatibility)
    if first != second:
        raise RuntimeError("Compatibility fixture inspection was not deterministic")
    return first


def main() -> None:
    """Parse arguments and execute the checkpoint journeys."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roadmap-command", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--workspace", type=Path)
    arguments = parser.parse_args()

    context = (
        nullcontext(validate_workspace(arguments.workspace))
        if arguments.workspace
        else tempfile.TemporaryDirectory(prefix="roadmap-checkpoint-")
    )
    with context as directory:
        snapshot = run_checkpoint(
            arguments.roadmap_command,
            arguments.fixture.resolve(strict=True),
            Path(directory),
        )
    print(json.dumps(snapshot, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
