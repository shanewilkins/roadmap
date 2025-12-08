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
    """Decorator: Ensure roadmap is initialized before command execution.

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


def handle_cli_operation_error(
    operation: str, entity_type: str | None = None, exit_code: int = 1
) -> Callable[[Callable], Callable]:
    """Decorator: Handle exceptions in CLI commands with logging and user feedback.

    Automatically:
    - Logs errors with context
    - Displays user-friendly error message
    - Exits with specified code

    Usage:
        @click.command()
        @handle_cli_operation_error(operation="archive_issue", entity_type="issue")
        def archive_issue(ctx, issue_id):
            # Any exception is caught, logged, and user is notified
            pass

    Args:
        operation: Name of operation (e.g., 'create_issue', 'archive_project')
        entity_type: Type of entity affected (e.g., 'issue', 'project')
        exit_code: Exit code to use on error
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except click.Abort:
                # User cancelled operation (Ctrl+C) - don't log as error
                raise
            except Exception as e:
                # Log the error
                log_context = {
                    "operation": operation,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                if entity_type:
                    log_context["entity_type"] = entity_type

                logger.error(f"{operation}_failed", **log_context)

                # Display user-friendly error
                console.print(
                    f"❌ Failed to {operation.replace('_', ' ')}: {e}",
                    style="bold red",
                )
                sys.exit(exit_code)

        return wrapper

    return decorator


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


def validate_required_fields(
    fields: dict[str, Any], exit_on_missing: bool = True
) -> bool:
    """Validate that required fields are provided.

    Args:
        fields: Dict of field_name -> field_value
        exit_on_missing: If True, exit on validation failure

    Returns:
        True if all fields valid, False otherwise

    Exits with error code 1 if exit_on_missing=True and validation fails.
    """
    missing = [name for name, value in fields.items() if not value]

    if missing:
        for field_name in missing:
            console.print(
                f"❌ Error: {field_name} is required",
                style="bold red",
            )
        if exit_on_missing:
            sys.exit(1)
        return False

    return True


def check_directory_exists(
    path: Any, description: str = "Directory", exit_on_missing: bool = True
) -> bool:
    """Check if directory exists.

    Args:
        path: Path object to check
        description: Human-readable name (e.g., "Issues directory")
        exit_on_missing: If True, exit on missing directory

    Returns:
        True if exists, False otherwise

    Exits with error code 1 if exit_on_missing=True and directory missing.
    """
    if not path.exists():
        console.print(
            f"❌ {description} not found: {path}",
            style="bold red",
        )
        if exit_on_missing:
            sys.exit(1)
        return False

    return True


def check_git_repo(git_manager: Any, exit_on_error: bool = True) -> bool:
    """Check if currently in a git repository.

    Args:
        git_manager: GitBranchManager or similar instance
        exit_on_error: If True, exit if not in git repo

    Returns:
        True if in git repo, False otherwise

    Exits with error code 1 if exit_on_error=True and not in git repo.
    """
    if not git_manager.is_in_git_repo():
        console.print(
            "❌ Not in a Git repository",
            style="bold red",
        )
        if exit_on_error:
            sys.exit(1)
        return False

    return True
