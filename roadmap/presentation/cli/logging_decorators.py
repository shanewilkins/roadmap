"""CLI command logging decorators for audit trail and observability.

Provides decorators to automatically log CLI command execution, timing,
user actions, and outcomes for comprehensive audit trail and debugging.
"""

import functools
import os
import time
from collections.abc import Callable
from typing import Any

import click  # type: ignore[import-not-found]

from roadmap.shared.logging import get_logger

logger = get_logger(__name__)


def get_current_user() -> str:
    """Get current user from environment or git config."""
    # Try environment first
    user = os.environ.get("USER") or os.environ.get("USERNAME")
    if user:
        return user

    # Try git config as fallback
    try:
        import git

        repo = git.Repo(search_parent_directories=True)  # type: ignore[attr-defined]
        try:
            return repo.config_reader().get_value("user", "name")
        except Exception:
            pass
    except Exception:
        pass

    return "unknown"


def log_command(
    command_name: str,
    entity_type: str | None = None,
    track_duration: bool = True,
    log_args: bool = False,
) -> Callable:
    """Decorator to log CLI command execution with audit trail.

    Args:
        command_name: Name of the command (e.g., "issue_create")
        entity_type: Type of entity affected (e.g., "issue", "milestone")
        track_duration: Whether to track and log command execution time
        log_args: Whether to log command arguments (use with caution for sensitive data)

    Example:
        @log_command("issue_create", entity_type="issue")
        @click.command()
        def create_issue(title, priority):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            user = get_current_user()
            start_time = time.time()

            # Log command initiation
            logger.info(
                f"{command_name}_initiated",
                user=user,
                entity_type=entity_type,
                args_logged=log_args,
            )

            if log_args:
                logger.debug(f"{command_name}_arguments", kwargs=kwargs)

            try:
                result = func(*args, **kwargs)

                # Log successful completion
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"{command_name}_completed",
                    user=user,
                    entity_type=entity_type,
                    duration_ms=duration_ms if track_duration else None,
                    status="success",
                )

                return result

            except click.Abort:
                # User cancelled (Ctrl+C or declined prompt)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"{command_name}_cancelled",
                    user=user,
                    entity_type=entity_type,
                    duration_ms=duration_ms if track_duration else None,
                )
                raise

            except Exception as e:
                # Log error with context
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"{command_name}_failed",
                    user=user,
                    entity_type=entity_type,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    duration_ms=duration_ms if track_duration else None,
                    is_user_error=isinstance(e, click.BadParameter | ValueError),
                )
                raise

        return wrapper

    return decorator


def log_audit_event(
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    reason: str | None = None,
) -> None:
    """Log an auditable user action with before/after state.

    Args:
        action: Action performed (create, update, delete, archive, restore)
        entity_type: Type of entity (issue, milestone, project)
        entity_id: ID of the entity
        before: Entity state before the action
        after: Entity state after the action
        reason: Reason for the action (if applicable)
    """
    user = get_current_user()
    logger.info(
        "audit_event",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
        before=before,
        after=after,
        reason=reason,
    )


def log_operation_duration(
    operation_name: str,
    warn_threshold_ms: int = 5000,
) -> Callable:
    """Decorator to log operation duration and identify slow operations.

    Args:
        operation_name: Name of the operation
        warn_threshold_ms: Threshold in milliseconds to warn about slow ops

    Example:
        @log_operation_duration("sync_issues", warn_threshold_ms=5000)
        def sync_to_github():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # Log at appropriate level based on duration
                if duration_ms > warn_threshold_ms:
                    logger.warning(
                        f"{operation_name}_slow",
                        duration_ms=duration_ms,
                        threshold_ms=warn_threshold_ms,
                    )
                else:
                    logger.debug(
                        f"{operation_name}_completed",
                        duration_ms=duration_ms,
                    )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"{operation_name}_failed",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    duration_ms=duration_ms,
                )
                raise

        return wrapper

    return decorator
