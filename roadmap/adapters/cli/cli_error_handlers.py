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
from typing import Any

import click

from roadmap.common.console import get_console
from roadmap.common.logging import get_logger
from roadmap.infrastructure.logging import (
    classify_error,
    is_error_recoverable,
    suggest_recovery,
)

console = get_console()
logger = get_logger(__name__)


# ===== Error Message Formatting =====
# (Legacy formatting functions removed - use infrastructure.logging instead)


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
