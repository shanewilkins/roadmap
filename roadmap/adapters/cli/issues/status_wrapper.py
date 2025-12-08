"""Generic helper for status change commands (block, unblock, close, start, etc.).

This module provides a unified pattern for syntactic sugar commands that update
issue status. Each command defines a StatusChangeConfig and calls apply_status_change()
to handle validation, updates, and user feedback consistently.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import click

from roadmap.common.console import get_console
from roadmap.core.domain import Status

if TYPE_CHECKING:
    from roadmap.core.application import Core

console = get_console()


@dataclass
class StatusChangeConfig:
    """Configuration for a status change command.

    Attributes:
        status: Target Status value
        emoji: Emoji to display in success message
        title_verb: Verb describing the action ("Blocked", "Unblocked", "Closed")
        title_style: Rich style for title line ("bold red", "bold green", etc.)
        status_display: String to show in status output ("🚫 Blocked", "🔄 In Progress", etc.)
        pre_check: Optional validation function that returns (is_valid: bool, error_msg: str | None)
    """

    status: Status
    emoji: str
    title_verb: str
    title_style: str
    status_display: str
    pre_check: Callable[[Any], tuple[bool, str | None]] | None = None


def apply_status_change(
    core: "Core",
    issue_id: str,
    config: StatusChangeConfig,
    reason: str | None = None,
) -> None:
    """Apply a status change to an issue with consistent feedback.

    This function:
    1. Ensures the issue exists
    2. Runs optional pre-checks (e.g., "is issue already blocked?")
    3. Updates the issue status
    4. Displays consistent success/failure feedback
    5. Raises click.Abort on failure

    Args:
        core: Core application object with issues manager
        issue_id: ID of issue to update
        config: StatusChangeConfig defining behavior
        reason: Optional reason for the change (displayed in feedback)

    Raises:
        click.Abort: If issue doesn't exist or update fails
    """
    from roadmap.adapters.cli.helpers import ensure_entity_exists

    # Ensure issue exists
    issue = ensure_entity_exists(core, "issue", issue_id)

    # Run pre-check if configured (e.g., "is issue already blocked?")
    if config.pre_check:
        is_valid, error_msg = config.pre_check(issue)
        if not is_valid:
            console.print(f"[yellow]⚠️  {error_msg}[/yellow]")
            return

    # Update status
    updated = core.issues.update(issue_id, status=config.status)

    if updated:
        # Success feedback
        console.print(
            f"{config.emoji} {config.title_verb} issue: {updated.title}",
            style=config.title_style,
        )
        console.print(f"   ID: {issue_id}", style="cyan")
        console.print(f"   Status: {config.status_display}", style="cyan")
        if reason:
            console.print(f"   Reason: {reason}", style="dim")
    else:
        # Failure feedback
        console.print(
            f"❌ Failed to {config.title_verb.lower()} issue: {issue_id}",
            style="bold red",
        )
        raise click.Abort()
