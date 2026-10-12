#!/usr/bin/env python3
"""Installed optional-adoption and durable requirement capture journey."""

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path


def canonical(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root / ".roadmap").rglob("*")
        if p.is_file() and p.suffix in {".md", ".yaml"}
    }


def journey(command, previous=None):
    with tempfile.TemporaryDirectory(prefix="roadmap-requirements-") as raw:
        root = Path(raw)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        env.update(
            HOME=str(root / "home"),
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
        )

        def run(*args, selected=command, code=0):
            result = subprocess.run(
                [str(selected), *args],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == code, result.stdout + result.stderr
            return result.stdout

        def requirement(*args):
            return json.loads(run("requirement", *args))

        run("init", "--skip-project", selected=previous or command)
        issue = run(
            "issue",
            "create",
            "--title",
            "Existing issue-only work",
            "--print-id",
            selected=previous or command,
        ).strip()
        before = canonical(root)
        assert requirement("list")["requirements"] == []
        assert not requirement("enable")["enabled"]
        assert canonical(root) == before
        requirement("enable", "--apply")
        if previous:
            refused = subprocess.run(
                [str(previous), "issue", "view", issue],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert refused.returncode != 0
            assert "schema_version" in refused.stdout + refused.stderr
        assert (
            canonical(root)[f".roadmap/issues/{issue}.md"]
            == before[f".roadmap/issues/{issue}.md"]
        )
        created = requirement(
            "create",
            "--type",
            "user",
            "--title",
            "Retain café intent",
            "--statement",
            "Full **Markdown**\n",
            "--criterion",
            "C1=Preserve UUID",
            "--owner",
            "Alice",
        )["requirement"]
        identity = created["id"]
        requirement("update", identity, "--owner", "Bob", "--priority", "high")
        assert (
            requirement("view", identity)["requirement"]["current_revision"]
            == created["current_revision"]
        )
        requirement("update", identity, "--title", "Revised intent")
        requirement("rekey", identity, "--key", "UR-012")
        current = requirement("view", "UR-012")["requirement"]
        assert current["id"] == identity and len(current["revisions"]) == 2
        path = root / ".roadmap/requirements" / f"{identity}.md"
        assert path.is_file()
        before = canonical(root)
        assert (
            requirement("list", "--owner", "Bob", "--priority", "high")["requirements"][
                0
            ]["id"]
            == identity
        )
        assert canonical(root) == before
        run("health", "fix", "--fix-type", "projection", "--yes")
        assert requirement("view", identity)["requirement"] == current
        assert json.loads(run("health", "scan", "--format", "json"))["findings"] == []
        after = canonical(root)
        requirement("enable", "--apply")
        assert canonical(root) == after
        return {
            "stable_uuid": True,
            "retained_issue_only_data": True,
            "read_canonical_writes": 0,
            "intent_revisions": 2,
            "rekey_preserved_path": True,
            "projection_rebuild_preserved_record": True,
            "released_version_refused_upgrade": bool(previous),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roadmap-command", type=Path, required=True)
    parser.add_argument("--previous-roadmap-command", type=Path)
    args = parser.parse_args()
    command = args.roadmap_command.resolve(strict=True)
    previous = (
        args.previous_roadmap_command.resolve(strict=True)
        if args.previous_roadmap_command
        else None
    )
    print(json.dumps(journey(command, previous), indent=2))


if __name__ == "__main__":
    main()
