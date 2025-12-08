"""CLI error handling and display helpers - shared across all command modules.

This module provides reusable error handling patterns for common CLI operations:
- Generic exception handling with user-friendly messages
- Operation failure messages with context
- Standardized error display formatting
- Recoverable vs fatal error handling

Consolidates duplicated error handling and display logic across all CLI commands.
"""

from typing import Any, Optional

from roadmap.common.console import get_console
from roadmap.infrastructure.logging import log_error_with_context

console = get_console()


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
    log_context: Optional[dict[str, Any]] = None,
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
    context: Optional[str] = None,
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
    details: Optional[dict[str, str]] = None,
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
    warning: str = None,
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
    suggestion: Optional[str] = None,
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
