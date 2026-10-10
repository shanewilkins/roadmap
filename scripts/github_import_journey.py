#!/usr/bin/env python3
"""Verify an installed importer with an offline gh fixture and isolated workspace."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def digests(root: Path):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (root / ".roadmap").rglob("*")
        if path.is_file() and path.suffix in {".md", ".yaml"}
    }


def run_journey(command: Path, root: Path):
    command = command.resolve(strict=True)
    source = root / "source.json"
    issue = {
        "number": 1,
        "node_id": "fixture-issue-1",
        "html_url": "https://github.com/owner/repo/issues/1",
        "title": "Upstream title",
        "body": "Full upstream Markdown",
        "state": "closed",
        "comments": 0,
        "user": {"login": "reporter"},
        "created_at": "2026-10-10T00:00:00Z",
        "updated_at": "2026-10-10T00:00:00Z",
        "labels": [],
        "assignees": [{"login": "reporter"}],
        "milestone": None,
    }
    source.write_text(
        json.dumps(
            {
                "issue": issue,
                "comments": [],
                "timeline": [
                    {"id": 1, "event": "closed", "actor": {"login": "reporter"}}
                ],
            }
        )
    )
    binaries = root / "bin"
    binaries.mkdir()
    executable = binaries / "gh"
    executable.write_text(
        f"#!{sys.executable}\nimport json,os,sys\nv=json.load(open(os.environ['ROADMAP_JOURNEY_SOURCE']))\np=sys.argv[4]\nprint(json.dumps([v['comments']] if '/comments?' in p else [v['timeline']] if '/timeline?' in p else v['issue']))\n"
    )
    executable.chmod(0o700)
    environment = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME"):
        environment.pop(key, None)
    environment.update(
        HOME=str(root / "home"),
        PATH=str(binaries) + os.pathsep + environment["PATH"],
        ROADMAP_JOURNEY_SOURCE=str(source),
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
    )

    def cli(*args):
        result = subprocess.run(
            [str(command), *args],
            cwd=root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout

    cli("init", "--skip-project")
    identity = cli(
        "issue",
        "create",
        "--title",
        "Local plan",
        "--assignee",
        "Alice",
        "--content",
        "Local context",
        "--print-id",
    ).strip()
    cli("issue", "update", identity, "--add-label", "github-source:owner/repo#1")
    cli("issue", "close", identity, "--reason", "Local decision")
    before = digests(root)
    preview = json.loads(cli("github", "import", "--repo", "owner/repo", "1"))
    assert preview["issues"][0]["issue_id"] == identity
    assert digests(root) == before
    applied = json.loads(
        cli("github", "import", "--repo", "owner/repo", "1", "--apply")
    )
    assert applied["issues"][0]["issue_id"] == identity
    before = digests(root)
    repeated = json.loads(
        cli("github", "import", "--repo", "owner/repo", "1", "--apply")
    )
    assert repeated["issues"][0]["action"] == "unchanged"
    assert digests(root) == before
    issue["title"] = "Changed source title"
    source.write_text(json.dumps({"issue": issue, "comments": [], "timeline": []}))
    cli("github", "import", "--repo", "owner/repo", "1", "--apply")
    record = json.loads(cli("issue", "view", identity, "--format", "json"))["record"][
        "issue"
    ]
    assert (
        record["title"] == "Local plan" and record["content"].strip() == "Local context"
    )
    assert record["status"] == "closed" and record["assignee"] == "Alice"
    assert len(record["comments"]) == 2
    assert len(list((root / ".roadmap/issues").glob("*.md"))) == 1
    assert json.loads(cli("health", "scan", "--format", "json"))["findings"] == []
    return {
        "version": cli("--version").strip(),
        "identity_reused": True,
        "unchanged_repeat_writes": 0,
        "source_revisions": 2,
        "local_decisions_preserved": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roadmap-command", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="roadmap-import-") as directory:
        print(json.dumps(run_journey(args.roadmap_command, Path(directory)), indent=2))


if __name__ == "__main__":
    main()
