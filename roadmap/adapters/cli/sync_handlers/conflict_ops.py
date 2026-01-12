"""Conflict detection and link/unlink operations."""
from __future__ import annotations

import sys
from typing import Any

import yaml
from structlog import get_logger

from roadmap.adapters.cli.services.sync_service import get_sync_backend
from roadmap.adapters.sync.sync_retrieval_orchestrator import (
    SyncRetrievalOrchestrator,
)
from roadmap.core.services.sync.sync_conflict_resolver import SyncConflictResolver
from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator

logger = get_logger(__name__)


def show_conflicts(core: Any, backend: str | None, verbose: bool, console_inst: Any) -> bool:
    """Handle the `--conflicts` flag to analyze and present conflicts."""
    config_file = core.roadmap_dir / "config.yaml"
    full_config: dict = {}

    if config_file.exists():
        with open(config_file) as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                full_config = loaded

    if backend:
        backend_type = backend.lower()
    else:
        if full_config.get("github", {}).get("sync_backend"):
            backend_type = str(full_config["github"]["sync_backend"]).lower()
        else:
            backend_type = "git"

    if backend_type == "github":
        github_config = full_config.get("github", {})
        from roadmap.infrastructure.security.credentials import CredentialManager

        cred_manager = CredentialManager()  # type: ignore[call-arg]
        token = cred_manager.get_token()

        config_dict = {
            "owner": github_config.get("owner"),
            "repo": github_config.get("repo"),
            "token": token,
        }
    else:
        config_dict = {}

    sync_backend = get_sync_backend(backend_type, core, config_dict)  # type: ignore
    if not sync_backend:
        console_inst.print("❌ Failed to initialize backend", style="bold red")
        sys.exit(1)

    state_comparator = SyncStateComparator()
    conflict_resolver = SyncConflictResolver()

    orchestrator = SyncRetrievalOrchestrator(
        core,
        sync_backend,
        state_comparator=state_comparator,
        conflict_resolver=conflict_resolver,
    )

    console_inst.print(
        "\n🔍 Analyzing conflicts between local, remote, and baseline...",
        style="bold cyan",
    )
    report = orchestrator.sync_all_issues(
        dry_run=True, force_local=False, force_remote=False
    )

    if report.conflicts_detected > 0:
        console_inst.print(
            f"\n⚠️  Found {report.conflicts_detected} conflict(s):",
            style="bold yellow",
        )

        for change in report.changes:
            if change.has_conflict:
                console_inst.print(
                    f"\n   📌 {change.issue_id}: {change.title}",
                    style="bold",
                )

                if change.local_changes:
                    console_inst.print(
                        f"      Local changes: {change.local_changes}",
                        style="yellow",
                    )

                if change.github_changes:
                    console_inst.print(
                        f"      Remote changes: {change.github_changes}",
                        style="blue",
                    )

                if change.flagged_conflicts:
                    console_inst.print(
                        f"      Flagged conflicts: {change.flagged_conflicts}",
                        style="bold red",
                    )

                if verbose:
                    console_inst.print(
                        f"      Full conflict info: {change.get_conflict_description()}",
                        style="dim",
                    )
    else:
        console_inst.print(
            "✅ No conflicts detected. Local and remote are in sync.",
            style="bold green",
        )

    return True


def handle_link_unlink(
    core: Any,
    backend: str | None,
    link: str | None,
    unlink: bool,
    issue_id: str | None,
    console_inst: Any,
) -> bool:
    """Handle `--link`/`--unlink` operations for manual remote ID management."""
    if not issue_id:
        console_inst.print(
            "❌ --issue-id is required when using --link or --unlink",
            style="bold red",
        )
        sys.exit(1)

    config_file = core.roadmap_dir / "config.yaml"
    full_config: dict = {}

    if config_file.exists():
        with open(config_file) as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                full_config = loaded

    if backend:
        backend_name = backend.lower()
    else:
        if full_config.get("github", {}).get("sync_backend"):
            backend_name = str(full_config["github"]["sync_backend"]).lower()
        else:
            backend_name = "git"

    issue = core.issues.get(issue_id)

    if not issue:
        console_inst.print(
            f"❌ Issue not found: {issue_id}",
            style="bold red",
        )
        sys.exit(1)

    if link:
        if issue.remote_ids is None:
            issue.remote_ids = {}
        issue.remote_ids[backend_name] = link
        core.issues.update(issue_id, remote_ids=issue.remote_ids)
        console_inst.print(
            f"✅ Linked issue {issue_id} to {backend_name}:{link}",
            style="bold green",
        )
    elif unlink:
        if issue.remote_ids and backend_name in issue.remote_ids:
            del issue.remote_ids[backend_name]
            core.issues.update(issue_id, remote_ids=issue.remote_ids)
            console_inst.print(
                f"✅ Unlinked issue {issue_id} from {backend_name}",
                style="bold green",
            )
        else:
            console_inst.print(
                f"⚠️  Issue {issue_id} is not linked to {backend_name}",
                style="bold yellow",
            )

    return True
