#!/usr/bin/env python3
"""Installed optional-adoption, requirement capture and governance journey."""

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
        revision = current["current_revision"]

        def transition(status):
            return requirement(
                "transition",
                identity,
                "--status",
                status,
                "--expected-revision",
                revision,
                "--reason",
                "Installed journey review",
            )["requirement"]

        def evidence(result):
            return requirement(
                "evidence",
                identity,
                "--criterion",
                "C1",
                "--result",
                result,
                "--reference",
                "artifact:installed-journey",
                "--expected-revision",
                revision,
                "--acceptance-id",
                acceptance_id,
            )["requirement"]

        acceptance_id = transition("accepted")["active_acceptance_id"]
        run(
            "requirement",
            "transition",
            identity,
            "--status",
            "verified",
            "--expected-revision",
            revision,
            "--reason",
            "Missing evidence refuses",
            code=1,
        )
        evidence("pass")
        transition("verified")
        assert evidence("fail")["status"] == "in-progress"
        assert evidence("pass")["status"] == "in-progress"
        current = transition("verified")
        old_acceptance = current["active_acceptance_id"]
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
        # Manual intent changes stale accepted proof without writes on reads.
        header, _body = path.read_text().rsplit("\n---\n", 1)
        path.write_text(header + "\n---\nManually changed intent\n")
        before = canonical(root)
        stale = requirement("view", identity)["requirement"]
        assert stale["status"] == "draft" and not stale["acceptance_current"]
        assert stale["verification"] == {"C1": "missing"}
        assert requirement("list", "--status", "verified")["requirements"] == []
        assert canonical(root) == before
        revision = stale["current_revision"]
        renewed = transition("accepted")
        acceptance_id = renewed["active_acceptance_id"]
        assert renewed["active_acceptance_id"] != old_acceptance
        assert len(renewed["evidence"]) == 3
        assert renewed["verification"] == {"C1": "missing"}
        evidence("pass")
        current = transition("verified")
        run("health", "fix", "--fix-type", "projection", "--yes")
        assert requirement("view", identity)["requirement"] == current
        after = canonical(root)
        requirement("enable", "--apply")
        assert canonical(root) == after
        return {
            "stable_uuid": True,
            "retained_issue_only_data": True,
            "read_canonical_writes": 0,
            "intent_revisions": len(current["revisions"]),
            "rekey_preserved_path": True,
            "projection_rebuild_preserved_record": True,
            "released_version_refused_upgrade": bool(previous),
            "explicit_acceptance_and_verification": True,
            "failed_evidence_demoted_verified": True,
            "manual_edit_staled_acceptance": True,
            "renewed_acceptance_required_fresh_evidence": True,
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
