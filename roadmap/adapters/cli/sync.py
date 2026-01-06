"""Top-level sync command - backend-agnostic interface to sync operations.

This command provides a unified interface for syncing with any backend
(GitHub, Git, etc.) without requiring the user to specify which backend.
The backend is automatically detected from configuration.
"""

import sys

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console


@click.command(name="sync")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without applying them",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed sync information",
)
@click.option(
    "--force-local",
    is_flag=True,
    help="Resolve all conflicts by keeping local changes",
)
@click.option(
    "--force-remote",
    is_flag=True,
    help="Resolve all conflicts by keeping remote changes",
)
@click.option(
    "--backend",
    type=click.Choice(["github", "git"], case_sensitive=False),
    default=None,
    help="Sync backend to use (auto-detected from config if not specified)",
)
@click.option(
    "--base",
    is_flag=True,
    help="Show the baseline state from the database (create if missing)",
)
@click.option(
    "--reset-baseline",
    is_flag=True,
    help="Force recalculate baseline from current state (WARNING: resets sync history)",
)
@click.option(
    "--conflicts",
    is_flag=True,
    help="Show detailed conflict information between local, remote, and baseline",
)
@click.option(
    "--push",
    is_flag=True,
    help="Push local changes to remote only (no pull)",
)
@click.option(
    "--pull",
    is_flag=True,
    help="Pull remote changes and merge locally only (no push)",
)
@click.option(
    "--link",
    type=str,
    metavar="REMOTE_ID",
    help="Link local issue to remote ID (requires --issue-id)",
)
@click.option(
    "--unlink",
    is_flag=True,
    help="Unlink local issue from remote (requires --issue-id)",
)
@click.option(
    "--issue-id",
    type=str,
    help="Local issue ID for link/unlink operations",
)
@click.option(
    "--baseline",
    type=click.Choice(["local", "remote"], case_sensitive=False),
    default=None,
    help="Strategy for first sync baseline (local=local is source of truth, remote=remote is source of truth)",
)
@click.pass_context
@require_initialized
def sync(
    ctx: click.Context,
    dry_run: bool,
    verbose: bool,
    force_local: bool,
    force_remote: bool,
    backend: str | None,
    base: bool,
    reset_baseline: bool,
    conflicts: bool,
    push: bool,
    pull: bool,
    link: str | None,
    unlink: bool,
    issue_id: str | None,
    baseline: str | None,
) -> None:
    """Sync roadmap with remote repository.

    This command provides intelligent two-way sync with automatic conflict
    resolution using three-way merge. It supports multiple backends:

    - **github**: Sync with GitHub issues API (requires GitHub configuration)
    - **git**: Sync with Git repository (works with any Git hosting)

    If no backend is specified, the command auto-detects from your config
    (set during `roadmap init`).

    **Sync Process:**
    1. Pull remote changes → merge with local using three-way merge
    2. Resolve conflicts automatically (when possible)
    3. Flag unresolvable conflicts for manual review
    4. Push local changes to remote
    5. User must manually run: git add, git commit, git push

    **Conflict Resolution:**
    - Critical fields (status, assignee, milestone) → flagged for review
    - Non-critical fields (labels, description) → automatically merged
    - Metadata (timestamps) → remote wins (remote is authoritative)

    **Examples:**
        # Sync with GitHub API
        roadmap sync

        # Preview changes (dry-run, no modifications)
        roadmap sync --dry-run

        # Sync with verbose output (shows all pulls and pushes)
        roadmap sync --verbose

        # First sync with local as baseline (local is source of truth)
        roadmap sync --baseline=local

        # First sync with remote as baseline (remote is source of truth)
        roadmap sync --baseline=remote

        # Resolve all conflicts locally (keep your changes)
        roadmap sync --force-local

        # Override backend selection
        roadmap sync --backend=github
    """
    from roadmap.adapters.cli.services.sync_service import get_sync_backend
    from roadmap.core.services.sync_conflict_resolver import SyncConflictResolver
    from roadmap.core.services.sync_state_comparator import SyncStateComparator

    core = ctx.obj["core"]
    console_inst = get_console()

    # Validate mutually exclusive flags
    if push and pull:
        console_inst.print(
            "❌ Cannot use both --push and --pull together. Choose one direction.",
            style="bold red",
        )
        sys.exit(1)

    # Handle --base flag to show baseline state
    if base:
        import yaml

        from roadmap.adapters.cli.services.sync_service import get_sync_backend
        from roadmap.adapters.sync.sync_retrieval_orchestrator import (
            SyncRetrievalOrchestrator,
        )

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

        # Prepare config for backend
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

        # Create orchestrator to get baseline
        orchestrator = SyncRetrievalOrchestrator(core, sync_backend)
        baseline_state = orchestrator.get_baseline_state()

        if baseline_state:
            console_inst.print(
                "\n📋 Baseline State (from database):", style="bold cyan"
            )
            console_inst.print(f"   Last Sync: {baseline_state.last_sync}")
            console_inst.print(f"   Backend: {baseline_state.backend}")
            console_inst.print(f"   Issues in baseline: {len(baseline_state.issues)}")

            if verbose and baseline_state.issues:
                console_inst.print("\n   Issues:", style="bold")
                for issue_id, issue_state in sorted(baseline_state.issues.items()):
                    console_inst.print(
                        f"      {issue_id}: {issue_state.title} [{issue_state.status}]"
                    )
        else:
            console_inst.print(
                "ℹ️  No baseline state found. Creating initial baseline from local state...",
                style="bold yellow",
            )

            # Create initial baseline from current local state
            initial_baseline = orchestrator._create_initial_baseline()

            if initial_baseline and len(initial_baseline.issues) > 0:
                # Convert SyncState to baseline dict for saving
                baseline_dict = {}
                for issue_id, issue_state in initial_baseline.issues.items():
                    baseline_dict[issue_id] = {
                        "status": issue_state.status,
                        "assignee": issue_state.assignee,
                        "milestone": issue_state.milestone,
                        "description": issue_state.description,
                        "labels": issue_state.labels,
                    }

                try:
                    # Use the StateManager to save baseline (properly formatted)
                    result = core.db.save_sync_baseline(baseline_dict)

                    if result:
                        console_inst.print(
                            "\n✅ Initial baseline created and saved to database:",
                            style="bold green",
                        )
                        console_inst.print(
                            f"   Last Sync: {initial_baseline.last_sync}",
                        )
                        console_inst.print(
                            f"   Backend: {initial_baseline.backend}",
                        )
                        console_inst.print(
                            f"   Issues in baseline: {len(initial_baseline.issues)}",
                        )

                        if verbose and initial_baseline.issues:
                            console_inst.print("\n   Issues:", style="bold")
                            for issue_id, issue_state in sorted(
                                initial_baseline.issues.items()
                            ):
                                console_inst.print(
                                    f"      {issue_id}: {issue_state.title} [{issue_state.status}]"
                                )
                    else:
                        console_inst.print(
                            "❌ Failed to save baseline to database",
                            style="bold red",
                        )
                        sys.exit(1)

                except Exception as e:
                    console_inst.print(
                        f"❌ Failed to save baseline to database: {str(e)}",
                        style="bold red",
                    )
                    sys.exit(1)
            else:
                console_inst.print(
                    "❌ No local issues found. Create some issues first with `roadmap create`.",
                    style="bold red",
                )
        return

    # Handle --reset-baseline flag to force recalculate baseline
    if reset_baseline:
        import sqlite3

        import yaml

        from roadmap.adapters.cli.services.sync_service import get_sync_backend
        from roadmap.adapters.sync.sync_retrieval_orchestrator import (
            SyncRetrievalOrchestrator,
        )

        # Warn user about the implications
        console_inst.print(
            "⚠️  WARNING: Resetting baseline will:",
            style="bold yellow",
        )
        console_inst.print("  • Clear all sync history")
        console_inst.print("  • Treat all current issues as the new baseline")
        console_inst.print("  • Next sync will see them as baseline (no changes)")
        console_inst.print()

        if not click.confirm("Continue with baseline reset?"):
            console_inst.print("Cancelled.", style="dim")
            return

        # Determine backend
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

        # Prepare config for backend
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

        # Clear existing baseline from database
        try:
            db_path = core.roadmap_dir / ".roadmap" / "db" / "state.db"
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sync_base_state")
                conn.commit()
                conn.close()
                console_inst.print("✅ Cleared existing baseline from database")
        except Exception as e:
            console_inst.print(
                f"⚠️  Warning: Could not clear old baseline: {str(e)}",
                style="yellow",
            )

        # Create fresh baseline from current local state
        orchestrator = SyncRetrievalOrchestrator(core, sync_backend)
        new_baseline = orchestrator._create_initial_baseline()

        if new_baseline and len(new_baseline.issues) > 0:
            try:
                db_path = core.roadmap_dir / ".roadmap" / "db" / "state.db"
                db_path.parent.mkdir(parents=True, exist_ok=True)

                import json
                from datetime import datetime

                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO sync_base_state (last_sync, data, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        datetime.now().isoformat(),
                        json.dumps(new_baseline.to_dict()),
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
                conn.close()

                console_inst.print(
                    "✅ Baseline reset successfully!",
                    style="bold green",
                )
                console_inst.print(
                    f"   Backend: {backend_type}",
                )
                console_inst.print(
                    f"   Issues in baseline: {len(new_baseline.issues)}",
                )

                if verbose and new_baseline.issues:
                    console_inst.print("\n   Issues in new baseline:", style="bold")
                    for issue_id, issue_state in sorted(new_baseline.issues.items()):
                        console_inst.print(
                            f"      {issue_id}: {issue_state.title} [{issue_state.status}]"
                        )

            except Exception as e:
                console_inst.print(
                    f"❌ Failed to save new baseline: {str(e)}",
                    style="bold red",
                )
                sys.exit(1)
        else:
            console_inst.print(
                "❌ No local issues found. Create issues first with `roadmap issue create`.",
                style="bold red",
            )
        return

    # Handle --conflicts flag to show conflict information
    if conflicts:
        import yaml

        from roadmap.adapters.cli.services.sync_service import get_sync_backend
        from roadmap.adapters.sync.sync_retrieval_orchestrator import (
            SyncRetrievalOrchestrator,
        )
        from roadmap.core.services.sync_conflict_resolver import SyncConflictResolver
        from roadmap.core.services.sync_state_comparator import SyncStateComparator

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

        # Prepare config for backend
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

        # Run conflict detection via dry-run
        state_comparator = SyncStateComparator()
        conflict_resolver = SyncConflictResolver()

        orchestrator = SyncRetrievalOrchestrator(
            core,
            sync_backend,
            state_comparator=state_comparator,
            conflict_resolver=conflict_resolver,
        )

        # Run sync in dry-run mode to detect conflicts
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

        return

    # Handle --link and --unlink flags for manual remote ID management
    if link or unlink:
        import yaml

        # Validate required --issue-id
        if not issue_id:
            console_inst.print(
                "❌ --issue-id is required when using --link or --unlink",
                style="bold red",
            )
            sys.exit(1)

        # Determine backend name
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

        # Load the issue
        issue = core.issues.get(issue_id)

        if not issue:
            console_inst.print(
                f"❌ Issue not found: {issue_id}",
                style="bold red",
            )
            sys.exit(1)

        # Perform link or unlink operation
        if link:
            # Link the issue to a remote ID
            if issue.remote_ids is None:
                issue.remote_ids = {}
            issue.remote_ids[backend_name] = link
            core.issues.update(issue_id, remote_ids=issue.remote_ids)
            console_inst.print(
                f"✅ Linked issue {issue_id} to {backend_name}:{link}",
                style="bold green",
            )
        elif unlink:
            # Unlink the issue from remote
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

        return

    try:
        import yaml

        # Load full config from file
        config_file = core.roadmap_dir / "config.yaml"
        full_config: dict = {}

        if config_file.exists():
            with open(config_file) as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    full_config = loaded

        # Determine backend to use
        if backend:
            backend_type = backend.lower()
        else:
            # Check if backend is explicitly set in config
            if full_config.get("github", {}).get("sync_backend"):
                backend_type = str(full_config["github"]["sync_backend"]).lower()
            else:
                # Default to git backend for self-hosting
                backend_type = "git"

        console_inst.print(
            f"🔄 Syncing with {backend_type.upper()} backend",
            style="bold cyan",
        )

        # Prepare config for backend
        if backend_type == "github":
            # GitHub backend expects owner, repo, token at top level
            github_config = full_config.get("github", {})

            # Get token from secure credentials storage
            from roadmap.infrastructure.security.credentials import CredentialManager

            cred_manager = CredentialManager()  # type: ignore[call-arg]
            token = cred_manager.get_token()

            config = {
                "owner": github_config.get("owner"),
                "repo": github_config.get("repo"),
                "token": token,
            }
        else:
            # Git backend doesn't need config
            config = {}

        # Create backend
        sync_backend = get_sync_backend(backend_type, core, config)  # type: ignore
        if not sync_backend:
            console_inst.print(
                f"❌ Failed to initialize {backend_type} backend",
                style="bold red",
            )
            if backend_type == "git":
                console_inst.print(
                    "   Ensure you're in a Git repository",
                    style="yellow",
                )
            elif backend_type == "github":
                console_inst.print(
                    "   GitHub config may be missing or incomplete",
                    style="yellow",
                )
            sys.exit(1)

        # Enforce baseline requirement - Phase 5 integration
        from roadmap.adapters.sync.sync_retrieval_orchestrator import (
            SyncRetrievalOrchestrator,
        )

        retrieval_orchestrator = SyncRetrievalOrchestrator(
            core,
            sync_backend,
        )

        # Check if baseline exists
        if not retrieval_orchestrator.has_baseline():
            console_inst.print(
                "\n⚠️  Baseline required for first sync",
                style="bold yellow",
            )
            console_inst.print(
                "   This establishes the agreed-upon starting state between local and remote."
            )

            # Use baseline strategy from option or default to REMOTE
            from roadmap.core.services.baseline_selector import BaselineStrategy

            if baseline:
                strategy = (
                    BaselineStrategy.LOCAL
                    if baseline.lower() == "local"
                    else BaselineStrategy.REMOTE
                )
            else:
                # Default to REMOTE if not specified
                strategy = BaselineStrategy.REMOTE

            # Ensure baseline with default strategy (avoids interactive hang)
            if not retrieval_orchestrator.ensure_baseline(strategy=strategy):
                console_inst.print(
                    "❌ Baseline creation failed",
                    style="bold red",
                )
                sys.exit(1)

            console_inst.print(
                "✅ Baseline created successfully",
                style="bold green",
            )
        else:
            console_inst.print(
                "✓ Using existing baseline for three-way merge",
                style="bold green",
            )

        # Create service instances
        state_comparator = SyncStateComparator()
        conflict_resolver = SyncConflictResolver()

        # Create cached orchestrator with progress support
        from roadmap.adapters.sync.sync_cache_orchestrator import (
            SyncCacheOrchestrator,
        )

        orchestrator = SyncCacheOrchestrator(
            core,
            sync_backend,
            state_comparator=state_comparator,
            conflict_resolver=conflict_resolver,
            show_progress=not dry_run,  # Show progress during real sync, not dry-run
        )

        # Run sync with specified flags
        report = orchestrator.sync_all_issues(
            dry_run=dry_run,
            force_local=force_local,
            force_remote=force_remote,
            show_progress=not dry_run,
        )

        if report.error:
            console_inst.print(f"❌ Sync error: {report.error}", style="bold red")
            sys.exit(1)

        # Filter report for push/pull operations
        if push:
            # Only show issues with local changes (being pushed)
            report.changes = [c for c in report.changes if c.local_changes]
            if report.changes:
                console_inst.print(
                    f"📤 Pushing {len(report.changes)} local change(s) to remote",
                    style="bold cyan",
                )
            else:
                console_inst.print(
                    "ℹ️  No local changes to push",
                    style="dim",
                )
        elif pull:
            # Only show issues with remote changes (being pulled)
            report.changes = [c for c in report.changes if c.github_changes]
            if report.changes:
                console_inst.print(
                    f"📥 Pulling {len(report.changes)} remote change(s) and merging locally",
                    style="bold cyan",
                )
            else:
                console_inst.print(
                    "ℹ️  No remote changes to pull",
                    style="dim",
                )

        # Display sync results report
        console_inst.print("\n[bold cyan]SYNC RESULTS:[/bold cyan]")
        if verbose:
            report.display_verbose()
        else:
            report.display_brief()

        console_inst.print()

        # If dry-run flag, note that no changes were applied
        if dry_run:
            console_inst.print(
                "[bold yellow]⚠️  Dry-run mode: No changes applied[/bold yellow]"
            )
            return

        console_inst.print(
            "✅ Sync completed successfully",
            style="bold green",
        )

    except Exception as exc:
        console_inst.print(
            f"❌ Unexpected error during sync: {exc}",
            style="bold red",
        )
        if verbose:
            raise
        sys.exit(1)
