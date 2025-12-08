"""CLI error handling and display helpers - shared across all command modules.

This module provides reusable error handling patterns for common CLI operations:
- Universal error handler with classification and context capture
- Decorator for automatic error handling in CLI commands
- Generic exception handling with user-friendly messages
- Operation failure messages with context
- Standardized error display formatting
- Recoverable vs fatal error handling

Consolidates duplicated error handling and display logic across all CLI commands.
"""

import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any

import click

from roadmap.common.console import get_console
from roadmap.common.logging import get_logger
from roadmap.infrastructure.logging import (
    classify_error,
    is_error_recoverable,
    log_error_with_context,
    suggest_recovery,
)

console = get_console()
logger = get_logger(__name__)


# ===== Error Message Formatting =====


def format_operation_error(
    operation: str,
    entity_type: str,
    entity_id: str,
    error: str,
    is_fatal: bool = True,
) -> str:
    """Format error message for failed operation with logging.

    Args:
        operation: Operation name (e.g., 'create', 'delete', 'archive')
        entity_type: Type of entity ('issue', 'milestone', 'project')
        entity_id: ID of entity
        error: Error message/exception text
        is_fatal: If True, error is fatal; if False, operation could retry

    Returns:
        Formatted error message ready for console display
    """
    emoji = "❌" if is_fatal else "⚠️"
    return f"{emoji} Failed to {operation} {entity_type} '{entity_id}': {error}"


def display_operation_error(
    operation: str,
    entity_type: str,
    entity_id: str,
    error: str,
    is_fatal: bool = True,
    log_context: dict[str, Any] | None = None,
) -> None:
    """Display error message and optionally log with context.

    Args:
        operation: Operation name (e.g., 'create', 'delete', 'archive')
        entity_type: Type of entity ('issue', 'milestone', 'project')
        entity_id: ID of entity
        error: Error message/exception text
        is_fatal: If True, error is fatal; if False, operation could retry
        log_context: Optional additional context to log
    """
    message = format_operation_error(operation, entity_type, entity_id, error, is_fatal)
    console.print(message, style="bold red")

    if log_context is not None:
        log_error_with_context(
            Exception(error),
            operation=f"{entity_type}_{operation}",
            entity_type=entity_type,
            additional_context=log_context,
        )


def display_not_found_error(
    entity_type: str,
    entity_id: str,
    context: str | None = None,
) -> None:
    """Display entity-not-found error message.

    Args:
        entity_type: Type of entity ('issue', 'milestone', 'project')
        entity_id: ID of entity that wasn't found
        context: Optional additional context (e.g., "in archive")
    """
    context_msg = f" {context}" if context else ""
    console.print(
        f"❌ {entity_type.capitalize()} '{entity_id}' not found{context_msg}.",
        style="bold red",
    )


def display_parse_error(
    entity_type: str,
    entity_id: str,
    error_detail: str,
) -> None:
    """Display error when parsing entity data fails.

    Args:
        entity_type: Type of entity being parsed
        entity_id: ID of entity
        error_detail: Details of parse error
    """
    console.print(
        f"❌ Failed to parse archived {entity_type} '{entity_id}': {error_detail}",
        style="bold red",
    )


def display_dry_run_mode() -> None:
    """Display message indicating dry-run mode is active."""
    console.print(
        "🔍 [DRY RUN] No changes will be made",
        style="bold blue",
    )


def display_dry_run_preview(
    operation: str,
    entity_type: str,
    entity_id: str,
    details: dict[str, str] | None = None,
) -> None:
    """Display preview of what would happen in dry-run mode.

    Args:
        operation: Operation being previewed ('archive', 'restore', etc.)
        entity_type: Type of entity
        entity_id: ID of entity
        details: Optional dict of detail_name -> detail_value to display
    """
    console.print(
        f"\n🔍 [DRY RUN] Would {operation} {entity_type}: {entity_id}",
        style="bold blue",
    )

    if details:
        for key, value in details.items():
            console.print(f"  {key}: {value}", style="cyan")


# ===== Status Validation Errors =====


def display_status_warning(
    entity_type: str,
    entity_id: str,
    current_status: str,
    warning: str | None = None,
) -> None:
    """Display warning about entity status not matching expected state.

    Args:
        entity_type: Type of entity
        entity_id: ID of entity
        current_status: Current status of entity
        warning: Optional custom warning message
    """
    if warning:
        msg = warning
    else:
        msg = f"⚠️  {entity_type.capitalize()} '{entity_id}' is not in expected state (status: {current_status})"
    console.print(msg, style="bold yellow")


def display_validation_error(
    field: str,
    error_detail: str,
    suggestion: str | None = None,
) -> None:
    """Display validation error for a field.

    Args:
        field: Name of field that failed validation
        error_detail: Details of validation failure
        suggestion: Optional suggestion for fixing the error
    """
    msg = f"❌ {field}: {error_detail}"
    if suggestion:
        msg += f"\n   💡 {suggestion}"
    console.print(msg, style="bold red")


# ===== Universal Error Handler (Phase 3b) =====


def generate_correlation_id() -> str:
    """Generate unique correlation ID for tracing errors through system."""
    return str(uuid.uuid4())[:8]


def extract_user_context() -> dict[str, Any]:
    """Extract user/session context from Click context."""
    try:
        ctx = click.get_current_context()
        return {
            "user": ctx.obj.get("user") if ctx.obj else None,
            "command": ctx.invoked_subcommand,
            "params": dict(ctx.params),
        }
    except RuntimeError:
        return {"user": None, "command": None, "params": {}}


def handle_cli_error(
    error: Exception,
    operation: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    context: dict[str, Any] | None = None,
    fatal: bool = True,
    include_traceback: bool = True,
) -> None:
    """Universal CLI error handler with classification, logging, and display.

    This is the single point of error handling for all CLI operations. It:
    1. Classifies the error (user/system/external)
    2. Generates correlation ID for tracing
    3. Captures user/command context
    4. Logs with full context to infrastructure logging
    5. Displays user-friendly message to console
    6. Suggests recovery action if applicable

    Args:
        error: The exception that occurred
        operation: Name of operation that failed (e.g., "archive_project")
        entity_type: Type of entity being operated on (e.g., "project")
        entity_id: ID of entity (e.g., project name)
        context: Optional additional context dict
        fatal: If True, error is fatal and command should exit
        include_traceback: If True, include full stack trace in logs
    """
    correlation_id = generate_correlation_id()
    user_context = extract_user_context()

    # Build comprehensive error context
    error_context = {
        "correlation_id": correlation_id,
        "operation": operation,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "error_class": type(error).__name__,
        "user": user_context.get("user"),
        "command": user_context.get("command"),
        "is_fatal": fatal,
    }

    if context:
        error_context.update(context)

    # Classify and log error
    classification = classify_error(error)
    recoverable = is_error_recoverable(error)
    recovery = suggest_recovery(error)

    error_context.update(
        {
            "classification": classification,
            "recoverable": recoverable,
            "suggested_action": recovery,
        }
    )

    # Log with full traceback if requested
    logger.error(
        f"{operation}_failed",
        exc_info=error,
        **error_context,
    )

    # Display user-friendly message
    emoji = "❌" if fatal else "⚠️"
    entity_msg = f" {entity_type}" if entity_type else ""
    id_msg = f" '{entity_id}'" if entity_id else ""

    message = f"{emoji} {operation.replace('_', ' ').title()}{entity_msg}{id_msg} failed: {str(error)}"
    console.print(message, style="bold red")

    # Add recovery suggestion if applicable
    if recoverable:
        console.print("   💡 Try again - this error may be temporary", style="cyan")
    elif recovery != "contact_support":
        action_msg = {
            "validate_input": "Check your input and try again",
            "check_connectivity": "Check network connection and try again",
            "manual_intervention": "Manual intervention may be required",
        }.get(recovery, "Contact support")
        console.print(f"   💡 {action_msg}", style="cyan")

    # Add correlation ID for support
    console.print(f"   📊 Error ID: {correlation_id}", style="dim")


def with_error_handling(
    operation: str,
    entity_type: str | None = None,
    fatal: bool = True,
) -> Callable:
    """Decorator for automatic error handling in CLI commands.

    Usage:
        @with_error_handling(operation="archive_project", entity_type="project")
        def archive_command(project_name: str):
            # Code here - decorator catches all exceptions
            pass

    Args:
        operation: Name of operation for logging
        entity_type: Type of entity (optional)
        fatal: If True, exit on error; if False, continue
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except click.Abort:
                # Let Click's Abort pass through (user cancelled)
                raise
            except Exception as e:
                # Extract entity_id from kwargs if available
                entity_id = (
                    kwargs.get("entity_id")
                    or kwargs.get("project_name")
                    or kwargs.get("issue_id")
                    or kwargs.get("milestone_id")
                )

                # Build operation-specific context
                error_context = {
                    "function": func.__name__,
                    **{
                        k: v
                        for k, v in kwargs.items()
                        if k not in ["ctx", "verbose", "force", "dry_run"]
                    },
                }

                handle_cli_error(
                    error=e,
                    operation=operation,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    context=error_context,
                    fatal=fatal,
                )

                if fatal:
                    raise SystemExit(1) from e
                else:
                    return None

        return wrapper

    return decorator
