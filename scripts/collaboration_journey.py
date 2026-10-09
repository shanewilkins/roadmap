#!/usr/bin/env python3
"""Verify installed Roadmap completion through a local bare remote and two clones."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
from contextlib import closing
from pathlib import Path


class Journey:
    def __init__(self, command: Path, root: Path):
        self.command = command.resolve(strict=True)
        self.root = root
        self.environment = os.environ.copy()
        for key in (
            "PYTHONPATH",
            "PYTHONHOME",
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
        ):
            self.environment.pop(key, None)
        self.environment.update(
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_AUTHOR_NAME="Journey contributor",
            GIT_AUTHOR_EMAIL="journey@example.invalid",
            GIT_COMMITTER_NAME="Journey contributor",
            GIT_COMMITTER_EMAIL="journey@example.invalid",
            GIT_TERMINAL_PROMPT="0",
        )

    def run(self, cwd: Path, args: list[str], *, expected: int = 0):
        environment = self.environment | {"HOME": str(self.root / f"{cwd.name}-home")}
        result = subprocess.run(
            args,
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != expected:
            raise RuntimeError(
                f"{args}: exit {result.returncode}\n{result.stdout}\n{result.stderr}"
            )
        return result

    def git(self, cwd: Path, *args: str, expected: int = 0):
        return self.run(cwd, ["git", *args], expected=expected)

    def cli(self, cwd: Path, *args: str, expected: int = 0):
        return self.run(cwd, [str(self.command), *args], expected=expected)

    def read(self, cwd: Path, *args: str):
        return json.loads(self.cli(cwd, *args, "--format", "json").stdout)


def canonical(root: Path):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (root / ".roadmap").rglob("*")
        if path.is_file() and path.suffix in {".md", ".yaml"}
    }


def seed(journey: Journey, bob: Path):
    journey.cli(bob, "init", "--skip-project")
    journey.cli(bob, "config", "set", "identity.name", "Bob")
    project = journey.cli(
        bob, "project", "create", "--title", "Shared project", "--print-id"
    ).stdout.strip()
    milestone = journey.cli(
        bob,
        "milestone",
        "create",
        "--title",
        "collaboration",
        "--project",
        project,
        "--print-id",
    ).stdout.strip()
    issue = journey.cli(
        bob,
        "issue",
        "create",
        "--title",
        "Shared work",
        "--milestone",
        milestone,
        "--content",
        "Implementation context",
        "--estimate",
        "2",
        "--print-id",
    ).stdout.strip()
    journey.cli(
        bob,
        "issue",
        "comment",
        "add",
        issue,
        "Bob's implementation evidence",
        "--author",
        "Bob",
    )
    (bob / "implementation.txt").write_text("before completion\n")
    journey.git(bob, "add", ".")
    journey.git(bob, "commit", "-m", "Seed shared canonical workspace")
    journey.git(bob, "push", "-u", "origin", "master")
    return project, milestone, issue


def complete(journey: Journey, bob: Path, issue: str):
    journey.git(bob, "checkout", "-b", "bob-completion")
    (bob / "implementation.txt").write_text("implementation complete\n")
    journey.cli(
        bob, "issue", "close", issue, "--reason", "Implemented and verified by Bob"
    )
    journey.git(bob, "add", ".")
    journey.git(bob, "commit", "-m", "Complete code and canonical work together")
    journey.git(bob, "checkout", "master")
    journey.git(
        bob, "merge", "--no-ff", "bob-completion", "-m", "Merge Bob's completed work"
    )
    journey.git(bob, "push", "origin", "master")


def verify_reads(journey: Journey, alice: Path, ids, stale: bytes):
    project, milestone, issue = ids
    database = alice / ".roadmap/db/projection.db"
    before = canonical(alice)
    checks = [
        ("detail", ["issue", "view", issue]),
        ("list", ["issue", "list", "--scope", "all", "--columns", "id,status"]),
        ("milestone", ["milestone", "view", milestone]),
        ("project", ["project", "view", project]),
    ]
    for state in ("stale", "missing"):
        for name, arguments in checks:
            if state == "stale":
                database.write_bytes(stale)
            else:
                database.unlink(missing_ok=True)
            payload = journey.read(alice, *arguments)
            if name == "detail":
                value = payload["record"]["issue"]
                assert value["id"] == issue and value["status"] == "closed"
                assert value["content"].strip() == "Implementation context"
                assert value["comments"][0]["body"] == "Bob's implementation evidence"
                assert value["comments"][0]["author"] == "Bob"
                assert (
                    value["history"][-1]["reason"] == "Implemented and verified by Bob"
                )
                assert value["assignee"] == "Bob"
            elif name == "list":
                assert payload["rows"] == [[issue, "closed"]]
            else:
                assert payload["record"]["closed_count"] == 1
                assert payload["record"]["issue_count"] == 1
                assert payload["record"]["progress"] == 100
            assert canonical(alice) == before
    assert (alice / "implementation.txt").read_text() == "implementation complete\n"
    assert not journey.git(alice, "status", "--porcelain").stdout.strip()


def verify_conflict(journey: Journey, bob: Path, alice: Path, ids):
    project, milestone, issue = ids
    path = Path(".roadmap/issues") / f"{issue}.md"
    journey.cli(
        alice, "issue", "update", issue, "--description", "Alice's concurrent context"
    )
    journey.git(alice, "add", str(path))
    journey.git(alice, "commit", "-m", "Alice changes context")
    journey.cli(
        bob, "issue", "update", issue, "--description", "Bob's concurrent context"
    )
    journey.git(bob, "add", str(path))
    journey.git(bob, "commit", "-m", "Bob changes context")
    journey.git(bob, "push", "origin", "master")
    journey.git(alice, "fetch", "origin")
    journey.git(alice, "merge", "origin/master", expected=1)
    # Resolve metadata first, leaving the real Git conflict in the Markdown body.
    incoming = journey.git(alice, "show", f"origin/master:{path.as_posix()}").stdout
    ours = journey.git(alice, "show", f":2:{path.as_posix()}").stdout
    header, incoming_body = incoming.split("\n---\n", 1)
    ours_body = ours.split("\n---\n", 1)[1]
    (alice / path).write_text(
        header
        + "\n---\n<<<<<<< HEAD\n"
        + ours_body.rstrip()
        + "\n"
        + "=======\n"
        + incoming_body.rstrip()
        + "\n>>>>>>> origin/master\n"
    )
    before = canonical(alice)
    health = json.loads(
        journey.cli(alice, "health", "scan", "--format", "json", expected=2).stdout
    )
    assert any(
        item["finding_id"] == "canonical.git-conflict" for item in health["findings"]
    )
    for arguments in (
        ["issue", "view", issue],
        ["issue", "list"],
        ["milestone", "view", milestone],
        ["project", "view", project],
    ):
        failure = journey.cli(alice, *arguments, "--format", "json", expected=1)
        assert "conflict" in (failure.stdout + failure.stderr).lower()
    assert canonical(alice) == before
    journey.git(alice, "checkout", "--theirs", str(path))
    journey.git(alice, "add", str(path))
    journey.git(alice, "commit", "-m", "Resolve conflict using Bob's canonical record")
    resolved = journey.read(alice, "issue", "view", issue)["record"]["issue"]
    assert resolved["status"] == "closed" and resolved["id"] == issue
    assert resolved["content"].strip() == "Bob's concurrent context"
    assert any(
        event["reason"] == "Implemented and verified by Bob"
        for event in resolved["history"]
    )
    assert (
        journey.read(alice, "milestone", "view", milestone)["record"]["closed_count"]
        == 1
    )
    assert (
        journey.read(alice, "project", "view", project)["record"]["closed_count"] == 1
    )
    assert journey.read(alice, "health", "scan")["findings"] == []


def run_journey(command: Path, root: Path):
    journey = Journey(command, root)
    journey.git(root, "init", "--bare", "--initial-branch=master", "remote.git")
    journey.git(root, "clone", "remote.git", "bob")
    bob, alice = root / "bob", root / "alice"
    ids = seed(journey, bob)
    journey.git(root, "clone", "remote.git", "alice")
    assert (
        journey.read(alice, "issue", "view", ids[2])["record"]["issue"]["status"]
        == "todo"
    )
    journey.cli(alice, "issue", "list")
    database = alice / ".roadmap/db/projection.db"
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT status FROM documents WHERE entity_id = ?", (ids[2],)
            ).fetchone()[0]
            == "todo"
        )
    stale = database.read_bytes()
    complete(journey, bob, ids[2])
    journey.git(alice, "pull", "--ff-only")
    assert database.read_bytes() == stale
    assert not (root / "alice-home/.config/roadmap/config.yaml").exists()
    verify_reads(journey, alice, ids, stale)
    verify_conflict(journey, bob, alice, ids)
    return {
        "version": journey.cli(alice, "--version").stdout.strip(),
        "first_reads": 8,
        "conflict_retry": "passed",
        "issue_id": ids[2],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roadmap-command", type=Path, required=True)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="roadmap-collaboration-") as directory:
        print(
            json.dumps(
                run_journey(arguments.roadmap_command, Path(directory)), indent=2
            )
        )


if __name__ == "__main__":
    main()
