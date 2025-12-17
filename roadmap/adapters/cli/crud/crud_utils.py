"""Shared utilities for CRUD operations across all entity types.

This module consolidates duplicate patterns from base_create, base_update,
and base_delete to eliminate code duplication.
"""

from typing import Any

from roadmap.adapters.cli.crud.crud_helpers import EntityType


def get_entity_by_type(
    core: Any, entity_type: EntityType, entity_id: str
) -> Any | None:
    """Get entity from core service by type.

    Consolidates the repeated _get_entity pattern from base_create,
    base_update, and base_delete.

    Args:
        core: The core application context
        entity_type: The type of entity to retrieve
        entity_id: The entity ID

    Returns:
        Entity object or None if not found
    """
    if entity_type == EntityType.ISSUE:
        return core.issues.get(entity_id)
    elif entity_type == EntityType.MILESTONE:
        return core.milestones.get(entity_id)
    elif entity_type == EntityType.PROJECT:
        return core.projects.get(entity_id)
    return None


def update_entity_by_type(
    core: Any, entity_type: EntityType, entity_id: str, update_dict: dict[str, Any]
) -> Any | None:
    """Update entity via appropriate service by type.

    Consolidates the repeated _update_entity pattern from base_create,
    base_update, and base_delete.

    Args:
        core: The core application context
        entity_type: The type of entity to update
        entity_id: The entity ID
        update_dict: Dictionary of fields to update

    Returns:
        Updated entity or None if failed
    """
    if entity_type == EntityType.ISSUE:
        return core.issues.update(entity_id, **update_dict)
    elif entity_type == EntityType.MILESTONE:
        return core.milestones.update(entity_id, **update_dict)
    elif entity_type == EntityType.PROJECT:
        return core.projects.update(entity_id, **update_dict)
    return None


def create_entity_by_type(
    core: Any, entity_type: EntityType, create_dict: dict[str, Any]
) -> Any | None:
    """Create entity via appropriate service by type.

    Args:
        core: The core application context
        entity_type: The type of entity to create
        create_dict: Dictionary of fields for new entity

    Returns:
        Created entity or None if failed
    """
    if entity_type == EntityType.ISSUE:
        return core.issues.create(**create_dict)
    elif entity_type == EntityType.MILESTONE:
        return core.milestones.create(**create_dict)
    elif entity_type == EntityType.PROJECT:
        return core.projects.create(**create_dict)
    return None


def delete_entity_by_type(core: Any, entity_type: EntityType, entity_id: str) -> bool:
    """Delete entity via appropriate service by type.

    Args:
        core: The core application context
        entity_type: The type of entity to delete
        entity_id: The entity ID

    Returns:
        True if deletion succeeded, False otherwise
    """
    if entity_type == EntityType.ISSUE:
        return core.issues.delete(entity_id)
    elif entity_type == EntityType.MILESTONE:
        return core.milestones.delete(entity_id)
    elif entity_type == EntityType.PROJECT:
        return core.projects.delete(entity_id)
    return False


def get_entity_title(entity: Any) -> str:
    """Get entity title/name.

    Consolidates the repeated _get_title pattern from base_create,
    base_update, and base_delete.

    Args:
        entity: The entity object

    Returns:
        Title or name string
    """
    if hasattr(entity, "title"):
        return entity.title
    elif hasattr(entity, "name"):
        return entity.name
    return str(entity)


def get_entity_id(entity: Any) -> str:
    """Get entity ID.

    Consolidates the repeated _get_id pattern from base_create,
    base_update, and base_delete.

    Args:
        entity: The entity object

    Returns:
        Entity ID string
    """
    return getattr(entity, "id", str(entity))


def format_entity_not_found_error(entity_type: EntityType, entity_id: str) -> str:
    """Format error message for entity not found.

    Consolidates the repeated entity-not-found error message pattern
    from base_update and base_delete.

    Args:
        entity_type: The type of entity that was not found
        entity_id: The entity ID that was not found

    Returns:
        Formatted error message string
    """
    return f"❌ {entity_type.value.title()} '{entity_id}' not found"
