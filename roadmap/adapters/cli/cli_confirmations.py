"""CLI confirmation and cancellation helpers - shared across all command modules.

This module provides reusable confirmation and entity-validation patterns for common CLI operations:
- Entity existence checks with standardized error messages
- Confirmation prompts with cancellation handling
- Archive existence validation
- Entity-not-found error messages

Consolidates duplicated confirmation and validation logic across issue, milestone, and project commands.
"""


import click  # type: ignore[import-not-found]

from roadmap.common.console import get_console

console = get_console()


# ===== Entity Validation =====


def check_entity_exists(core, entity_type: str, entity_id: str, entity_lookup=None):
    """Check if entity exists, display error and return False if not found.

    Args:
        core: RoadmapCore instance
        entity_type: Type of entity ('issue', 'milestone', 'project')
        entity_id: ID or name of entity to validate
        entity_lookup: Optional pre-fetched entity to check instead of looking up

    Returns:
        The entity object if found, False if not found (already displays error message)
    """
    if entity_lookup is not None:
        entity = entity_lookup
    else:
        entity_collection = getattr(core, f"{entity_type}s", None)
        if entity_collection is None:
            console.print(
                f"❌ Invalid entity type: {entity_type}",
                style="bold red",
            )
            return False
        entity = entity_collection.get(entity_id)

    if not entity:
        console.print(
            f"❌ {entity_type.capitalize()} '{entity_id}' not found.",
            style="bold red",
        )
        return False

    return entity


# ===== Confirmation Prompts =====


def confirm_action(prompt: str, default: bool = False) -> bool:
    """Show confirmation prompt and handle cancellation.

    Displays user-friendly cancellation message if user declines.

    Args:
        prompt: Confirmation prompt text
        default: Default value if user just presses Enter

    Returns:
        True if confirmed, False if cancelled (message already displayed)
    """
    if not click.confirm(prompt, default=default):
        console.print("❌ Cancelled.", style="yellow")
        return False
    return True
