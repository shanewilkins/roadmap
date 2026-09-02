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
from typing import Any, TypeVar

import click  # type: ignore[import-not-found]
from rich.console import Console  # type: ignore[import-not-found]

from roadmap.application.failures import ApplicationFailure
from roadmap.domain.failures import DomainFailure

console = Console()

F = TypeVar("F", bound=Callable[..., Any])


def invoke(operation: Callable[[], Any]) -> Any:
    """Translate stable application/domain failures into Click failures."""
    try:
        return operation()
    except (ApplicationFailure, DomainFailure, ValueError) as error:
        raise click.ClickException(str(error)) from error


def projection_warning(result: Any) -> None:
    if getattr(result, "projection_stale", False):
        click.echo("Warning: SQLite projection is stale; canonical Markdown was saved.")


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
