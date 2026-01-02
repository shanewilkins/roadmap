"""Top-level sync command - backend-agnostic interface to sync operations.

This command provides a unified interface for syncing with any backend
(GitHub, Git, etc.) without requiring the user to specify which backend.
The backend is automatically detected from configuration.
"""

import sys

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.core.services.github_integration_service import GitHubIntegrationService


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
@click.pass_context
@require_initialized
def sync(
    ctx: click.Context,
    dry_run: bool,
    verbose: bool,
    force_local: bool,
    force_remote: bool,
    backend: str | None,
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

        # Resolve all conflicts locally (keep your changes)
        roadmap sync --force-local

        # Override backend selection
        roadmap sync --backend=github
    """
    from roadmap.adapters.cli.services.sync_service import get_sync_backend
    from roadmap.adapters.sync import (
        GenericSyncOrchestrator,
        detect_backend_from_config,
    )
    from roadmap.core.services.sync_conflict_resolver import SyncConflictResolver
    from roadmap.core.services.sync_state_comparator import SyncStateComparator

    core = ctx.obj["core"]
    console_inst = get_console()

    try:
        # Load config from both locations
        gh_service = GitHubIntegrationService(core, core.roadmap_dir / "config.yaml")
        config_result = gh_service.get_github_config()

        # Handle both tuple (real code) and dict (mocked code) returns
        if isinstance(config_result, tuple):
            token, owner, repo = config_result
            config = {
                "owner": owner,
                "repo": repo,
                "token": token,
            }
        else:
            config = config_result or {}

        # Determine backend to use
        if backend:
            backend_type = backend.lower()
        else:
            backend_type = detect_backend_from_config(config)
            if not backend_type:
                console_inst.print(
                    "❌ Could not auto-detect sync backend from config",
                    style="bold red",
                )
                console_inst.print(
                    "   Please run: roadmap init",
                    style="yellow",
                )
                sys.exit(1)

        console_inst.print(
            f"🔄 Syncing with {backend_type.upper()} backend",
            style="bold cyan",
        )

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

        # Create service instances
        state_comparator = SyncStateComparator()
        conflict_resolver = SyncConflictResolver()

        # Create orchestrator with services
        orchestrator = GenericSyncOrchestrator(
            core,
            sync_backend,
            state_comparator=state_comparator,
            conflict_resolver=conflict_resolver,
        )

        # Run sync with specified flags
        report = orchestrator.sync_all_issues(
            dry_run=dry_run,
            force_local=force_local,
            force_remote=force_remote,
        )

        if report.error:
            console_inst.print(f"❌ Sync error: {report.error}", style="bold red")
            sys.exit(1)

        # Display report
        if verbose:
            report.display_verbose()
        else:
            report.display_brief()

        console_inst.print()

        # If dry-run flag, note that no changes were applied
        if dry_run:
            console_inst.print("[dim]Dry-run mode: No changes applied[/dim]")
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
