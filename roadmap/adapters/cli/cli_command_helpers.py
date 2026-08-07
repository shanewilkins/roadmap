"""CLI command helpers - Consolidated patterns for common CLI operations.

Provides decorators and functions to reduce duplication in CLI commands:
- Initialization checks
- Entity validation
- Operation error handling
- Confirmation dialogs
"""

import functools
import sys
from collections.abc import Callable
from typing import Any, TypeVar

import click  # type: ignore[import-not-found]
from rich.console import Console  # type: ignore[import-not-found]

from roadmap.common.logging import get_logger

logger = get_logger(__name__)
console = Console()

F = TypeVar("F", bound=Callable[..., Any])


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
