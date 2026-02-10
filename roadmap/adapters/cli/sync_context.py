"""Helper utilities for the `sync` CLI command.

This module contains initialization and baseline helpers extracted from
`sync.py` to reduce its size and improve maintainability.
"""

from rich.progress import Progress, SpinnerColumn, TextColumn
from structlog import get_logger

logger = get_logger(__name__)


def _resolve_backend_and_init(core, backend, get_sync_backend_callable):
    """Resolve backend_type and initialize the sync backend instance.

    Returns tuple `(backend_type, sync_backend)` where `sync_backend` may
    be None if initialization failed.
    """
    import yaml

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
            "sync_settings": github_config.get("sync_settings", {}),
        }
    else:
        config_dict = {}

    sync_backend = get_sync_backend_callable(backend_type, core, config_dict)  # type: ignore[arg-type]
    return backend_type, sync_backend


def _clear_baseline_db(core, console_inst):
    """Clear baseline entries from the SQLite DB if present.

    Logs warnings but does not raise on failure.
    """
    import sqlite3

    try:
        db_path = core.db_dir / "state.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sync_base_state")
            conn.commit()
            conn.close()
            console_inst.print("✅ Cleared existing baseline from database")
    except OSError as e:
        logger.warning(
            "baseline_clear_failed",
            operation="reset_baseline",
            error_type=type(e).__name__,
            error=str(e),
            is_recoverable=True,
            severity="operational",
        )
        console_inst.print(
            f"⚠️  Warning: Could not clear old baseline: {str(e)}", style="yellow"
        )
    except Exception as e:
        logger.warning(
            "baseline_clear_failed",
            operation="reset_baseline",
            error_type=type(e).__name__,
            error=str(e),
            severity="operational",
        )
        console_inst.print(
            f"⚠️  Warning: Could not clear old baseline: {str(e)}", style="yellow"
        )


def _create_and_save_baseline(
    core, sync_backend, backend_type, console_inst, verbose
) -> bool:
    """Create an initial baseline from local issues and save it to DB.

    Returns True on success, False otherwise.
    """
    from roadmap.adapters.sync.sync_retrieval_orchestrator import (
        SyncRetrievalOrchestrator,
    )

    orchestrator = SyncRetrievalOrchestrator(core, sync_backend)

    console_inst.print(
        "\n📊 Creating baseline from current local state...", style="cyan"
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Loading issues from disk...", total=None)
            new_baseline = orchestrator._create_initial_baseline()
            progress.update(task, completed=True)

            if not new_baseline or len(new_baseline.base_issues) == 0:
                logger.warning("baseline_reset_no_issues", operation="reset_baseline")
                console_inst.print(
                    "❌ No local issues found. Create issues first with `roadmap issue create`.",
                    style="bold red",
                )
                return False

            console_inst.print(
                f"✅ Loaded {len(new_baseline.base_issues)} issues", style="green"
            )

    except Exception as e:
        logger.error(
            "baseline_creation_failed",
            operation="reset_baseline",
            error_type=type(e).__name__,
            error=str(e),
            error_classification="sync_error",
            severity="system_error",
        )
        console_inst.print(f"❌ Failed to load issues: {str(e)}", style="bold red")
        return False

    # Save baseline to database
    console_inst.print("💾 Saving baseline to database...", style="cyan")

    try:
        baseline_dict = {
            issue_id: {
                "status": issue_state.status,
                "assignee": issue_state.assignee,
                "headline": issue_state.headline,
                "content": issue_state.content,
                "labels": issue_state.labels,
            }
            for issue_id, issue_state in new_baseline.base_issues.items()
        }

        result = core.db.save_sync_baseline(baseline_dict)

        if result:
            console_inst.print(
                "\n✅ Initial baseline created and saved to database:",
                style="bold green",
            )
            console_inst.print(f"   Last Sync: {new_baseline.last_sync_time}")
            console_inst.print(
                f"   Issues in baseline: {len(new_baseline.base_issues)}"
            )

            if verbose and new_baseline.base_issues:
                console_inst.print("\n   Issues:", style="bold")
                for issue_id, issue_state in sorted(new_baseline.base_issues.items()):
                    console_inst.print(
                        f"      {issue_id}: {issue_state.title} [{issue_state.status}]"
                    )
            return True
        else:
            console_inst.print(
                "❌ Failed to save baseline to database", style="bold red"
            )
            return False

    except Exception as e:
        logger.error(
            "baseline_save_failed",
            operation="reset_baseline",
            error_type=type(e).__name__,
            error=str(e),
            error_classification="database_error",
        )
        console_inst.print(f"❌ Failed to save baseline: {str(e)}", style="bold red")
        return False


def _prune_db_issues_missing_files(core, console_inst, dry_run: bool) -> None:
    """Remove DB issues that no longer have matching local files."""
    import sqlite3

    issues_dir = core.roadmap_dir / "issues"
    if not issues_dir.exists():
        return

    try:
        from roadmap.adapters.persistence.parser.issue import IssueParser

        local_issue_ids: set[str] = set()
        for file_path in issues_dir.glob("**/*.md"):
            try:
                issue = IssueParser.parse_issue_file(file_path)
            except Exception:
                continue
            if getattr(issue, "id", None):
                local_issue_ids.add(str(issue.id))

        if not local_issue_ids:
            return

        db_path = core.db_dir / "state.db"
        if not db_path.exists():
            return

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id FROM issues").fetchall()
        db_issue_ids = {row["id"] for row in rows}

        stale_ids = sorted(db_issue_ids - local_issue_ids)
        if not stale_ids:
            conn.close()
            return

        if dry_run:
            console_inst.print(
                f"🧹 DB preflight: {len(stale_ids)} issues would be removed (no local file)",
                style="yellow",
            )
            conn.close()
            return

        placeholders = ",".join("?" * len(stale_ids))
        conn.execute(f"DELETE FROM issues WHERE id IN ({placeholders})", stale_ids)
        conn.commit()
        conn.close()

        console_inst.print(
            f"🧹 DB preflight: removed {len(stale_ids)} stale issues", style="green"
        )
    except Exception as e:
        logger.warning(
            "db_issue_prune_failed",
            error=str(e),
            error_type=type(e).__name__,
            severity="operational",
        )
        console_inst.print(
            f"⚠️  Warning: Could not prune DB issues: {str(e)}", style="yellow"
        )


def _init_sync_context(
    core,
    backend,
    baseline_option,
    dry_run,
    verbose,
    console_inst,
    enable_duplicate_detection=True,
    title_threshold=0.90,
    content_threshold=0.85,
    auto_resolve_threshold=0.95,
):
    """Initialize backend, orchestrator, and required services for sync command.

    Returns tuple: (backend_type, sync_backend, orchestrator, pre_sync_baseline, pre_sync_issue_count, state_comparator, conflict_resolver)
    """
    from roadmap.adapters.cli.services.sync_service import get_sync_backend
    from roadmap.adapters.sync.sync_retrieval_orchestrator import (
        SyncRetrievalOrchestrator,
    )

    # Local imports for services used by the helper
    from roadmap.core.services.sync.sync_conflict_resolver import SyncConflictResolver
    from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator

    # Resolve backend and initialize
    backend_type, sync_backend = _resolve_backend_and_init(
        core, backend, get_sync_backend
    )

    console_inst.print(
        f"🔄 Syncing with {backend_type.upper()} backend", style="bold cyan"
    )

    _prune_db_issues_missing_files(core, console_inst, dry_run)
    _repair_remote_links(core, console_inst, backend_type, dry_run)
    orchestrator = SyncRetrievalOrchestrator(
        core,
        sync_backend,
        enable_duplicate_detection=enable_duplicate_detection,
        duplicate_title_threshold=title_threshold,
        duplicate_content_threshold=content_threshold,
        duplicate_auto_resolve_threshold=auto_resolve_threshold,
    )

    # Pre-sync baseline for comparison
    pre_sync_baseline = (
        orchestrator.get_baseline_state() if not baseline_option else None
    )
    pre_sync_issue_count = (
        len(pre_sync_baseline.base_issues) if pre_sync_baseline else 0
    )

    # Helper services
    state_comparator = SyncStateComparator()
    conflict_resolver = SyncConflictResolver()

    return (
        backend_type,
        sync_backend,
        orchestrator,
        pre_sync_baseline,
        pre_sync_issue_count,
        state_comparator,
        conflict_resolver,
    )


def _repair_remote_links(core, console_inst, backend_type: str, dry_run: bool) -> None:
    """Repair remote link cache from YAML before sync.

    Args:
        core: RoadmapCore instance
        console_inst: Rich console
        backend_type: Backend name (github, git, etc.)
        dry_run: Whether sync is in dry-run mode
    """
    if backend_type.lower() != "github":
        return

    if dry_run:
        console_inst.print("[dim]Skipping remote link repair in dry-run mode[/dim]")
        return

    try:
        validation_data = core.validation.collect_remote_link_validation_data(
            core.issues_dir, backend_name="github"
        )
        report = core.validation.build_remote_link_report(
            validation_data["yaml_remote_ids"], validation_data["db_links"]
        )
        if not (
            report.get("missing_in_db")
            or report.get("extra_in_db")
            or report.get("duplicate_remote_ids")
        ):
            return

        yaml_remote_ids = validation_data["yaml_remote_ids"]
        should_prune = bool(yaml_remote_ids)

        results = core.validation.apply_remote_link_fixes(
            yaml_remote_ids,
            report,
            backend_name="github",
            prune_extra=should_prune,
            dedupe=True,
            dry_run=False,
        )
        fixed = results.get("fixed_count", 0)
        removed = results.get("removed_count", 0)
        deduped = results.get("deduped_count", 0)
        console_inst.print(
            f"🔧 Remote links repaired: +{fixed} / -{removed} / deduped {deduped}",
            style="dim",
        )
    except Exception as e:
        logger.warning(
            "remote_link_repair_failed",
            error=str(e),
            error_type=type(e).__name__,
            severity="operational",
        )
        console_inst.print(
            "[yellow]⚠️  Remote link repair failed; continuing sync[/yellow]"
        )
