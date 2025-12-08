"""CLI confirmation and cancellation helpers - shared across all command modules.

This module provides reusable confirmation and entity-validation patterns for common CLI operations:
- Entity existence checks with standardized error messages
- Confirmation prompts with cancellation handling
- Archive existence validation
- Entity-not-found error messages

Consolidates duplicated confirmation and validation logic across issue, milestone, and project commands.
"""

from typing import Any, Optional

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


def check_archived_entity_exists(archive_dir, entity_id: str, entity_type: str):
    """Check if archived entity file exists.
    
    Args:
        archive_dir: Path to archive directory
        entity_id: ID of entity to find
        entity_type: Type of entity ('issue', 'milestone', 'project')
        
    Returns:
        Path to archived file if found, False if not found (already displays error message)
    """
    archive_file = archive_dir / f"{entity_id}.json"
    if not archive_file.exists():
        console.print(
            f"❌ Archived {entity_type} '{entity_id}' not found.",
            style="bold red",
        )
        return False
    return archive_file


def check_archive_directory_exists(roadmap_dir, entity_type: str):
    """Check if archive directory exists for entity type.
    
    Args:
        roadmap_dir: Path to .roadmap directory
        entity_type: Type of entity ('issue', 'milestone', 'project')
        
    Returns:
        Path to archive directory if exists, False if not found (already displays error message)
    """
    archive_dir = roadmap_dir / "archive" / f"{entity_type}s"
    if not archive_dir.exists():
        console.print(
            f"❌ No archived {entity_type}s found.",
            style="bold red",
        )
        return False
    return archive_dir


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


def confirm_archive_action(entity_type: str, entity_id: Optional[str] = None, warning: Optional[str] = None) -> bool:
    """Show confirmation for archiving action with optional warning.
    
    Args:
        entity_type: Type of entity ('issue', 'milestone', 'project')
        entity_id: Optional ID/name for specific entity
        warning: Optional warning message to display before confirmation
        
    Returns:
        True if confirmed, False if cancelled
    """
    if warning:
        console.print(warning, style="bold yellow")
    
    entity_label = f"{entity_type} '{entity_id}'" if entity_id else f"{entity_type}(s)"
    if not click.confirm(
        f"\n[bold]Archive {entity_label}?[/bold]", 
        default=False
    ):
        console.print("❌ Cancelled.", style="yellow")
        return False
    return True


def confirm_restore_action(entity_type: str, entity_count: int = 1) -> bool:
    """Show confirmation for restore action.
    
    Args:
        entity_type: Type of entity ('issue', 'milestone', 'project')
        entity_count: Number of entities to restore (for message clarity)
        
    Returns:
        True if confirmed, False if cancelled
    """
    entity_label = f"{entity_count} {entity_type}(s)" if entity_count > 1 else entity_type
    if not click.confirm(f"\nProceed with restore? ({entity_label})", default=False):
        console.print("❌ Cancelled.", style="yellow")
        return False
    return True


def confirm_override_warning() -> bool:
    """Show confirmation for override/force action with warning.
    
    Returns:
        True if confirmed, False if cancelled
    """
    if not click.confirm("Archive anyway?", default=False):
        console.print("❌ Cancelled.", style="yellow")
        return False
    return True


def confirm_close_milestone(milestone_name: str, open_issue_count: int, force: bool = False) -> bool:
    """Show confirmation for closing milestone with open issues.
    
    Args:
        milestone_name: Name of milestone to close
        open_issue_count: Number of open issues in milestone
        force: If True, skip confirmation
        
    Returns:
        True if confirmed, False if cancelled
    """
    if force:
        return True
    
    warning_msg = f"⚠️  {open_issue_count} issue(s) still open in milestone '{milestone_name}'"
    console.print(warning_msg, style="bold yellow")
    
    if not click.confirm("Close milestone anyway?", default=False):
        console.print("❌ Milestone close cancelled.", style="yellow")
        return False
    return True


def confirm_delete_action(entity_type: str, entity_id: Optional[str] = None) -> bool:
    """Show confirmation for delete action.
    
    Args:
        entity_type: Type of entity ('issue', 'milestone', 'project')
        entity_id: Optional ID/name for specific entity
        
    Returns:
        True if confirmed, False if cancelled
    """
    entity_label = f"{entity_type}" if not entity_id else f"{entity_type} '{entity_id}'"
    if not click.confirm(f"Delete {entity_label}?", default=False):
        console.print("❌ Deletion cancelled.", style="yellow")
        return False
    return True
