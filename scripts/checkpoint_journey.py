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


def _clean_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    return environment


def _run(
    command: list[str],
    workspace: Path,
    *,
    parse_json: bool = False,
) -> str | Any:
    print(f"+ {' '.join(command)}", flush=True)
    result = subprocess.run(
        command,
        cwd=workspace,
        env=_clean_environment(),
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


def inspect_fixture(roadmap: Path, fixture: Path, workspace: Path) -> dict[str, Any]:
    """Load the compatibility fixture and return a stable semantic snapshot."""
    verify_fixture_digests(fixture)
    _materialize_fixture(fixture, workspace)
    expected = json.loads((fixture / "expected.json").read_text())

    projects = _run([str(roadmap), "project", "list"], workspace)
    milestones = _run([str(roadmap), "milestone", "list"], workspace)
    issues = _run(
        [str(roadmap), "issue", "list", "--format", "json"],
        workspace,
        parse_json=True,
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
    )
    closed_issue = _run(
        [str(roadmap), "issue", "view", expected["closed_issue_id"]], workspace
    )
    archived = _run([str(roadmap), "issue", "archive", "--list"], workspace)

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
    stats = _rebuild_projection(roadmap, workspace)
    if stats.get("files_failed"):
        raise RuntimeError("Compatibility fixture projection rebuild failed")
    if canonical_digests(workspace) != before_rebuild:
        raise RuntimeError("Fixture projection rebuild changed canonical documents")
    with sqlite3.connect(workspace / ".roadmap" / "db" / "state.db") as connection:
        projected = dict(connection.execute("SELECT id, archived FROM issues"))
    expected_projection = {
        expected["visible_issue_id"]: 0,
        expected["closed_issue_id"]: 0,
        expected["archived_issue_id"]: 1,
    }
    if projected != expected_projection:
        raise RuntimeError("Fixture projection rebuild was not semantically equivalent")
    return snapshot


def _extract_created_issue_id(output: str) -> str:
    match = re.search(
        r"(?:\bID:\s*|Created issue:\s*\[)([0-9a-f]{8}(?:-[0-9a-f-]{27})?)",
        output,
    )
    if not match:
        raise RuntimeError("Could not read the created issue ID")
    return match.group(1)


def _rebuild_projection(roadmap: Path, workspace: Path) -> dict[str, Any]:
    for database_file in (workspace / ".roadmap" / "db").glob("state.db*"):
        database_file.unlink()
    python = roadmap.parent / ("python.exe" if os.name == "nt" else "python")
    program = (
        "from pathlib import Path; "
        "from roadmap.infrastructure.coordination.core import RoadmapCore; "
        "core=RoadmapCore(Path.cwd()); "
        "stats=core.db.full_rebuild_from_git(Path.cwd()/'.roadmap'); "
        "core.close(); print(__import__('json').dumps(stats, default=str))"
    )
    return _run([str(python), "-c", program], workspace, parse_json=True)


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
            "--skip-github",
        ],
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

    before_rebuild = canonical_digests(workspace)
    stats = _rebuild_projection(roadmap, workspace)
    if stats.get("files_failed"):
        raise RuntimeError("SQLite projection rebuild failed")
    if canonical_digests(workspace) != before_rebuild:
        raise RuntimeError("SQLite rebuild changed canonical documents")
    with sqlite3.connect(workspace / ".roadmap" / "db" / "state.db") as connection:
        row = connection.execute(
            "SELECT id FROM issues WHERE id = ?", (issue_id,)
        ).fetchone()
    if row is None:
        raise RuntimeError("SQLite projection rebuild omitted the active issue")

    _run([str(roadmap), "health", "--format", "json"], workspace, parse_json=True)
    _run(
        [str(roadmap), "health", "fix", "--dry-run", "--format", "json"],
        workspace,
        parse_json=True,
    )
    _run(["git", "init"], workspace)
    _run([str(roadmap), "git", "status"], workspace)


def run_checkpoint(roadmap: Path, fixture: Path, workspace: Path) -> dict[str, Any]:
    """Run fresh and compatibility journeys below a validated workspace."""
    workspace = validate_workspace(workspace)
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError("Checkpoint workspace must be empty")
    workspace.mkdir(parents=True, exist_ok=True)
    fresh = workspace / "fresh"
    compatibility = workspace / "compatibility"
    fresh.mkdir()
    compatibility.mkdir()
    run_fresh_journey(roadmap.resolve(strict=True), fresh)
    first = inspect_fixture(roadmap, fixture, compatibility)

    shutil.rmtree(compatibility)
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
