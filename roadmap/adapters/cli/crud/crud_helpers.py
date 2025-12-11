"""Shared CRUD operation helpers and utilities.

This module provides common functionality for Create, Update, Delete,
Archive, and Restore operations across all entity types.
"""

from enum import Enum
from pathlib import Path
from typing import Any

from roadmap.common.console import get_console


class EntityType(str, Enum):
    """Entity types for CRUD operations."""

    ISSUE = "issue"
    MILESTONE = "milestone"
    PROJECT = "project"


class CRUDOperation(str, Enum):
    """CRUD operation types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ARCHIVE = "archive"
    RESTORE = "restore"


def format_entity_title(entity_type: EntityType, entity: Any) -> str:
    """Get display title for entity (handles different entity types).

    Args:
        entity_type: The type of entity
        entity: The entity object

    Returns:
        Formatted title string
    """
    if entity_type == EntityType.ISSUE:
        return entity.title
    elif entity_type == EntityType.MILESTONE:
        return entity.name
    elif entity_type == EntityType.PROJECT:
        return entity.name
    return str(entity)


def format_entity_id(entity_type: EntityType, entity: Any) -> str:
    """Get display ID for entity.

    Args:
        entity_type: The type of entity
        entity: The entity object

    Returns:
        Entity ID string
    """
    return getattr(entity, "id", str(entity))


def validate_entity_exists(
    core: Any,
    entity_type: EntityType,
    entity_id: str,
    console: Any = None,
) -> tuple[bool, str | None]:
    """Check if entity exists.

    Args:
        core: The core application context
        entity_type: The type of entity to check
        entity_id: The ID of the entity
        console: Optional console for output

    Returns:
        Tuple of (exists: bool, error_message: Optional[str])
    """
    try:
        if entity_type == EntityType.ISSUE:
            entity = core.issues.get(entity_id)
        elif entity_type == EntityType.MILESTONE:
            entity = core.milestones.get(entity_id)
        elif entity_type == EntityType.PROJECT:
            entity = core.projects.get(entity_id)
        else:
            return False, f"Unknown entity type: {entity_type}"

        if entity is None:
            return False, f"{entity_type.value.title()} '{entity_id}' not found"

        return True, None
    except Exception as e:
        return False, f"Error checking {entity_type.value}: {str(e)}"


def collect_archive_files(
    archive_dir: Path,
    entity_type: EntityType,
) -> list[Path]:
    """Collect all archived files of a specific entity type.

    Args:
        archive_dir: Path to the archive directory
        entity_type: The type of entity to collect

    Returns:
        List of archive file paths
    """
    if not archive_dir.exists():
        return []

    # For issues, search recursively (may be in subfolders)
    if entity_type == EntityType.ISSUE:
        return list(archive_dir.rglob("*.md"))

    # For milestones and projects, search in root
    return list(archive_dir.glob("*.md"))


def get_archive_dir(entity_type: EntityType) -> Path:
    """Get archive directory for entity type.

    Args:
        entity_type: The type of entity

    Returns:
        Path to archive directory
    """
    roadmap_dir = Path.cwd() / ".roadmap"
    entity_name = entity_type.value  # "issue", "milestone", "project"
    return roadmap_dir / "archive" / (entity_name + "s")  # pluralize


def get_active_dir(entity_type: EntityType) -> Path:
    """Get active directory for entity type.

    Args:
        entity_type: The type of entity

    Returns:
        Path to active directory
    """
    roadmap_dir = Path.cwd() / ".roadmap"
    entity_name = entity_type.value  # "issue", "milestone", "project"
    return roadmap_dir / (entity_name + "s")  # pluralize


def display_archive_success(
    entity_type: EntityType,
    archived_count: int,
    skipped_count: int,
    console: Any = None,
) -> None:
    """Display success message for archive operation.

    Args:
        entity_type: The type of entity
        archived_count: Number of archived items
        skipped_count: Number of skipped items
        console: Optional console for output
    """
    if console is None:
        console = get_console()

    plural = "s" if archived_count != 1 else ""
    console.print(
        f"✅ Archived {archived_count} {entity_type.value}{plural}",
        style="green",
    )
    if skipped_count > 0:
        console.print(
            f"⚠️  Skipped {skipped_count} (already archived or errors)",
            style="yellow",
        )


def display_restore_success(
    entity_type: EntityType,
    restored_count: int,
    failed_count: int,
    console: Any = None,
) -> None:
    """Display success message for restore operation.

    Args:
        entity_type: The type of entity
        restored_count: Number of restored items
        failed_count: Number of failed restorations
        console: Optional console for output
    """
    if console is None:
        console = get_console()

    plural = "s" if restored_count != 1 else ""
    console.print(
        f"✅ Restored {restored_count} {entity_type.value}{plural}",
        style="green",
    )
    if failed_count > 0:
        console.print(
            f"❌ Failed to restore {failed_count} {entity_type.value}(s)",
            style="red",
        )
