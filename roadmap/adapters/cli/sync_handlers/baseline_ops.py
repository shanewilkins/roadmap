"""Baseline state operations: show, reset, clear, capture."""

from __future__ import annotations

import sqlite3
import sys
from typing import Any

import click
from rich.progress import Progress, SpinnerColumn, TextColumn
from structlog import get_logger

from roadmap.adapters.cli.services.sync_service import get_sync_backend
from roadmap.adapters.sync.sync_retrieval_orchestrator import (
    SyncRetrievalOrchestrator,
)

logger = get_logger(__name__)


def show_baseline(
    core: Any, backend: str | None, verbose: bool, console_inst: Any
) -> bool:
    """Handle the `--base` flag: show or create baseline state."""
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
        }
    else:
        config_dict = {}

    sync_backend = get_sync_backend(backend_type, core, config_dict)  # type: ignore
    if not sync_backend:
        console_inst.print("❌ Failed to initialize backend", style="bold red")
        sys.exit(1)

    orchestrator = SyncRetrievalOrchestrator(core, sync_backend)
    baseline_state = orchestrator.get_baseline_state()

    if baseline_state:
        console_inst.print("\n📋 Baseline State (from database):", style="bold cyan")
        console_inst.print(f"   Last Sync: {baseline_state.last_sync_time}")
        console_inst.print(f"   Issues in baseline: {len(baseline_state.base_issues)}")

        if verbose and baseline_state.base_issues:
            console_inst.print("\n   Issues:", style="bold")
            for issue_id, issue_state in sorted(baseline_state.base_issues.items()):
                console_inst.print(
                    f"      {issue_id}: {issue_state.title} [{issue_state.status}]"
                )
    else:
        console_inst.print(
            "ℹ️  No baseline state found. Creating initial baseline from local state...",
            style="bold yellow",
        )

        initial_baseline = orchestrator._create_initial_baseline()

        if initial_baseline and len(initial_baseline.base_issues) > 0:
            baseline_dict = {}
            for issue_id, issue_state in initial_baseline.base_issues.items():
                baseline_dict[issue_id] = {
                    "status": issue_state.status,
                    "assignee": issue_state.assignee,
                    "headline": issue_state.headline,
                    "content": issue_state.content,
                    "labels": issue_state.labels,
                }

            try:
                result = core.db.save_sync_baseline(baseline_dict)

                if result:
                    console_inst.print(
                        "\n✅ Initial baseline created and saved to database:",
                        style="bold green",
                    )
                    console_inst.print(
                        f"   Last Sync: {initial_baseline.last_sync_time}"
                    )
                    console_inst.print(
                        f"   Issues in baseline: {len(initial_baseline.base_issues)}",
                    )

                    if verbose and initial_baseline.base_issues:
                        console_inst.print("\n   Issues:", style="bold")
                        for issue_id, issue_state in sorted(
                            initial_baseline.base_issues.items()
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
    return True


def reset_baseline(
    core: Any, backend: str | None, verbose: bool, console_inst: Any
) -> bool:
    """Handle the `--reset-baseline` flag: force recalculation of baseline."""
    from roadmap.adapters.cli.sync_context import (
        _clear_baseline_db,
        _create_and_save_baseline,
        _resolve_backend_and_init,
    )

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
        return True

    backend_type, sync_backend = _resolve_backend_and_init(
        core, backend, get_sync_backend
    )
    if not sync_backend:
        console_inst.print("❌ Failed to initialize backend", style="bold red")
        sys.exit(1)

    _clear_baseline_db(core, console_inst)

    success = _create_and_save_baseline(
        core, sync_backend, backend_type, console_inst, verbose
    )
    if not success:
        sys.exit(1)

    return True


def clear_baseline(core: Any, backend: str | None, console_inst: Any) -> bool:
    """Handle the `--clear-baseline` flag to clear baseline without syncing."""
    console_inst.print(
        "⚠️  WARNING: Clearing baseline will:",
        style="bold yellow",
    )
    console_inst.print("  • Delete all sync history")
    console_inst.print("  • Next sync will rebuild baseline from scratch")
    console_inst.print()

    if not click.confirm("Continue with baseline clear?"):
        console_inst.print("Cancelled.", style="dim")
        return True

    try:
        db_path = core.roadmap_dir / ".roadmap" / "db" / "state.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sync_base_state")
            conn.commit()
            conn.close()
            console_inst.print("✅ Baseline cleared successfully", style="bold green")
        else:
            console_inst.print(
                "ℹ️  No baseline file found (already empty)",
                style="dim",
            )
    except OSError as e:
        logger.error(
            "baseline_clear_failed",
            operation="clear_baseline",
            error_type=type(e).__name__,
            error=str(e),
            is_recoverable=True,
            severity="system_error",
        )
        console_inst.print(
            f"❌ Failed to clear baseline: {str(e)}",
            style="bold red",
        )
        sys.exit(1)
    except Exception as e:
        logger.error(
            "baseline_clear_failed",
            operation="clear_baseline",
            error_type=type(e).__name__,
            error=str(e),
            severity="system_error",
        )
        console_inst.print(
            f"❌ Failed to clear baseline: {str(e)}",
            style="bold red",
        )
        sys.exit(1)
    return True


def capture_and_save_post_sync_baseline(
    core: Any, console_inst: Any, pre_sync_issue_count: int, verbose: bool
) -> None:
    """Capture local issues and save them as the post-sync baseline."""
    try:
        baseline_dict = {}

        all_local_issues = core.issues.list_all_including_archived()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console_inst,
            transient=True,
        ) as progress:
            task = progress.add_task(
                f"Building baseline... (0/{len(all_local_issues)})",
                total=len(all_local_issues),
            )

            for idx, issue in enumerate(all_local_issues):
                labels = issue.labels or []
                sorted_labels = sorted(labels) if labels else []

                baseline_dict[issue.id] = {
                    "status": (
                        issue.status.value
                        if hasattr(issue.status, "value")
                        else str(issue.status)
                    ),
                    "assignee": issue.assignee,
                    "milestone": issue.milestone,
                    "headline": issue.headline,
                    "content": issue.content,
                    "labels": sorted_labels,
                }

                progress.update(
                    task,
                    description=f"Building baseline... ({idx + 1}/{len(all_local_issues)})",
                    advance=1,
                )

        post_sync_issue_count = len(baseline_dict)

        try:
            result = core.db.save_sync_baseline(baseline_dict)
            if result:
                console_inst.print(
                    f"   After:  {post_sync_issue_count} issues in baseline"
                )
            if post_sync_issue_count != pre_sync_issue_count:
                diff = post_sync_issue_count - pre_sync_issue_count
                symbol = "+" if diff > 0 else ""
                console_inst.print(
                    f"   Change: {symbol}{diff} issue(s)",
                    style="green" if diff > 0 else "yellow",
                )
            if verbose:
                console_inst.print(
                    "✅ Baseline updated with post-sync state", style="dim"
                )
        except OSError as e:
            logger.error(
                "post_sync_baseline_save_exception",
                operation="save_post_sync_baseline",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=True,
                severity="system_error",
                suggested_action="check_disk_space",
            )
            if verbose:
                console_inst.print(
                    f"⚠️  Warning: Could not update baseline: {str(e)}", style="yellow"
                )
        except Exception as e:
            logger.error(
                "post_sync_baseline_save_exception",
                operation="save_post_sync_baseline",
                error_type=type(e).__name__,
                error=str(e),
                severity="system_error",
                error_classification="sync_error",
            )
            if verbose:
                console_inst.print(
                    f"⚠️  Warning: Could not update baseline: {str(e)}", style="yellow"
                )
    except Exception as e:
        logger.error(
            "post_sync_baseline_capture_exception",
            operation="capture_post_sync_baseline",
            error_type=type(e).__name__,
            error=str(e),
            severity="system_error",
            error_classification="sync_error",
        )
        if verbose:
            console_inst.print(
                f"⚠️  Warning: Could not update baseline: {str(e)}", style="yellow"
            )
