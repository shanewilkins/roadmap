"""CLI command helpers - Consolidated patterns for common CLI operations.

Provides decorators and functions to reduce duplication in CLI commands:
- Initialization checks
- Entity validation
- Operation error handling
- Confirmation dialogs
"""

import functools
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TypeVar

import click  # type: ignore[import-not-found]
from rich.console import Console  # type: ignore[import-not-found]

from roadmap.application.failures import ApplicationFailure
from roadmap.domain.failures import DomainFailure

console = Console()

F = TypeVar("F", bound=Callable[..., Any])


def verbose_message(enabled: bool, message: str) -> None:
    if enabled:
        click.echo(message, err=True)


def validate_list_mode(list_mode: bool, selectors: Sequence[bool]) -> None:
    if list_mode and any(selectors):
        raise click.UsageError(
            "--list cannot be combined with selectors or mutation options"
        )


def confirm_override_action(dry_run: bool, force: bool, yes: bool, prompt: str) -> None:
    if force and not yes and not dry_run:
        click.echo(
            "Deprecated through 0.3: --force also skips confirmation; in 0.4 use --force --yes for override and consent.",
            err=True,
        )
    if not dry_run and not (yes or force):
        click.confirm(prompt, abort=True)


def write_report(content: str, path: Path, description: str) -> None:
    """Create a report exclusively; never replace a user's existing file."""
    try:
        with path.open("x", encoding="utf-8", newline="") as stream:
            stream.write(content)
            if not content.endswith("\n"):
                stream.write("\n")
    except FileExistsError as error:
        raise click.ClickException(
            f"Refusing to overwrite existing report: {path}"
        ) from error
    except OSError as error:
        raise click.ClickException(f"Cannot write report {path}: {error}") from error
    click.echo(f"Exported {description} to {path}", err=True)


def compatibility_warnings(ctx: click.Context) -> None:
    """Keep old spellings through 0.3; announce their 0.4 replacement."""
    marker = f"compatibility:{ctx.command_path}"
    if ctx.meta.get(marker):
        return
    ctx.meta[marker] = True
    name = ctx.command.name
    replacements: dict[str, str] = {}
    if name not in {"archive", "restore", "cleanup", "migrate", "fix"}:
        replacements["verbose"] = (
            "remove --verbose; use global --debug for unexpected failures"
        )
    if name == "init":
        replacements["force"] = (
            "remove --force; initialization is idempotent and never overwrites existing canonical data"
        )
        replacements.update(
            dict.fromkeys(
                ("interactive", "yes", "template", "template_path"),
                "remove this option; init is noninteractive and templates are deferred",
            )
        )
    if name == "cleanup":
        replacements.update(
            {
                "force": "use --yes",
                "backups_only": "remove --backups-only; cleanup only handles backups",
                **dict.fromkeys(
                    ("check_folders", "check_duplicates", "check_malformed"),
                    "use health scan for canonical diagnostics",
                ),
            }
        )
    if name == "restore":
        replacements["force"] = "use --yes"
    if name in {"scan", "check", "health", "db-integrity", "fix"}:
        replacements.update(
            dict.fromkeys(
                ("details", "group_by", "show_ids", "limit", "json_output"),
                "use health scan filters, --summary-only, or --format",
            )
        )
    if name == "kanban":
        replacements.update(
            {
                "compact": "remove --compact; there is one board layout",
                "no_color": "remove --no-color; the board is uncolored",
            }
        )
    for parameter, replacement in replacements.items():
        if (
            ctx.get_parameter_source(parameter)
            is click.core.ParameterSource.COMMANDLINE
        ):
            click.echo(
                f"Deprecated through 0.3; removed in 0.4: --{parameter.replace('_', '-')}; {replacement}.",
                err=True,
            )


def validate_branch_options(ctx: click.Context, git_branch: bool) -> None:
    """Reject explicit branch-only arguments before any canonical mutation."""
    if git_branch:
        return
    for name in ("branch_name", "checkout", "force"):
        if ctx.get_parameter_source(name) is click.core.ParameterSource.COMMANDLINE:
            raise click.UsageError(f"--{name.replace('_', '-')} requires --git-branch")


def invoke(operation: Callable[[], Any]) -> Any:
    """Translate stable application/domain failures into Click failures."""
    try:
        return operation()
    except (ApplicationFailure, DomainFailure, ValueError) as error:
        raise click.ClickException(str(error)) from error


def projection_warning(result: Any) -> None:
    if getattr(result, "projection_stale", False):
        click.echo(
            "Warning: SQLite projection is stale; canonical Markdown was saved. "
            "Preview repair with 'roadmap health fix --fix-type projection --dry-run'.",
            err=True,
        )


def echo_batch_result(
    noun: str,
    items: Sequence[Any],
    dry_run: bool,
    *,
    action: str,
    label: Callable[[Any], str] = lambda item: str(item.name),
) -> None:
    """Echo the "<verb> <noun> <id>: <label>" summary shared by batch
    archive/restore commands. ``action`` is the base verb (e.g. "archive",
    "restore"); both currently used verbs conjugate regularly to their past
    tense for the non-dry-run wording.
    """
    past_tense = action + ("d" if action.endswith("e") else "ed")
    verb = f"Would {action}" if dry_run else past_tense.capitalize()
    for item in items:
        click.echo(f"{verb} {noun} {item.id}: {label(item)}")
    if not items:
        click.echo(f"No matching {noun}s.")


def echo_archived_list(
    noun: str,
    values: Sequence[Any],
    label: Callable[[Any], str] = lambda item: str(item.name),
) -> None:
    """Echo the archived-entity listing shared by the "--list" branch of
    the project/milestone archive commands."""
    if not values:
        click.echo(f"No archived {noun}s.")
    for item in values:
        click.echo(f"{item.id}  {label(item)}")


def require_initialized(func: Callable) -> Callable:
    """Require roadmap to be initialized before command execution.

    Usage:
        @click.command()
        @click.pass_context
        @require_initialized
        def my_command(ctx: click.Context):
            # ctx.obj["core"] is guaranteed to be initialized
            pass

    Exits with error code 1 if not initialized.
    """

    @functools.wraps(func)
    def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
        compatibility_warnings(ctx)
        core = ctx.obj.get("core")
        if not core or not core.is_initialized():
            console.print(
                "❌ Roadmap not initialized. Run 'roadmap init' first.",
                style="bold red",
            )
            ctx.exit(1)
        return func(ctx, *args, **kwargs)

    return wrapper


def ensure_entity_exists(
    core: Any, entity_type: str, entity_id: str, entity: Any = None
) -> Any:
    """Ensure entity exists, exit with error if not found.

    Args:
        core: RoadmapCore instance
        entity_type: Type of entity ('issue', 'project', 'milestone')
        entity_id: ID of entity to look up
        entity: Pre-fetched entity (if None, will look up via core)

    Returns:
        The entity object

    Exits with error code 1 if entity not found.
    """
    if entity is None:
        # Fetch from core
        entity_collection = getattr(core, f"{entity_type}s", None)
        if entity_collection is None:
            console.print(
                f"❌ Invalid entity type: {entity_type}",
                style="bold red",
            )
            sys.exit(1)
        entity = entity_collection.get(entity_id)

    if not entity:
        console.print(
            f"❌ {entity_type.capitalize()} not found: {entity_id}",
            style="bold red",
        )
        sys.exit(1)

    return entity


def confirm_action(prompt: str, default: bool = False, force: bool = False) -> bool:
    """Prompt user to confirm an action.

    Args:
        prompt: Confirmation prompt text
        default: Default answer if user just presses Enter
        force: If True, skip prompt and return True (for --force flag)

    Returns:
        True if user confirms, False otherwise (displays cancellation message)
    """
    if force:
        return True

    if not click.confirm(prompt, default=default):
        console.print("❌ Cancelled.", style="yellow")
        return False

    return True
