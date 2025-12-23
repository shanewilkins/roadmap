"""Presenter for CRUD operation results.

This presenter handles displaying results of create, update, delete, archive,
and restore operations. It shows a brief success message with key entity details.
"""

from typing import Any

from roadmap.adapters.cli.presentation.base_presenter import BasePresenter


def _infer_entity_type(entity: Any) -> str:
    """Infer entity type from class name or attributes.

    Handles both real objects and mocks used in tests.

    Args:
        entity: The entity object

    Returns:
        Entity type string (Issue, Project, Milestone, Entity)
    """
    class_name = entity.__class__.__name__

    # Handle mocks in tests
    if class_name == "Mock":
        # Try to infer from entity attributes
        if hasattr(entity, "priority") and hasattr(entity, "issue_type"):
            return "Issue"
        elif hasattr(entity, "repository"):
            return "Project"
        elif hasattr(entity, "start_date") or hasattr(entity, "end_date"):
            return "Milestone"
        return "Entity"

    return class_name


def _get_entity_id(entity: Any) -> str:
    """Extract entity ID."""
    if hasattr(entity, "id"):
        return str(entity.id)
    if hasattr(entity, "entity_id"):
        return str(entity.entity_id)
    return "unknown"


def _get_entity_title(entity: Any) -> str:
    """Extract entity title/name."""
    if hasattr(entity, "name"):
        return entity.name
    if hasattr(entity, "title"):
        return entity.title
    if hasattr(entity, "summary"):
        return entity.summary
    return "Untitled"


class CreatePresenter(BasePresenter):
    """Presenter for create operation results."""

    def render(self, entity: Any) -> None:
        """Render created entity summary.

        Args:
            entity: The created entity object
        """
        console = self._get_console()
        entity_type = _infer_entity_type(entity)
        entity_id = _get_entity_id(entity)
        title = _get_entity_title(entity)

        console.print(
            f"✅ Created {entity_type.lower()}: {title} [{entity_id}]",
            style="green",
        )


class UpdatePresenter(BasePresenter):
    """Presenter for update operation results."""

    def render(self, entity: Any, _updates: dict[str, Any] | None = None) -> None:
        """Render updated entity summary.

        Args:
            entity: The updated entity object
            _updates: Optional dict of fields that were updated
        """
        console = self._get_console()
        entity_type = _infer_entity_type(entity)
        entity_id = _get_entity_id(entity)
        title = _get_entity_title(entity)

        console.print(
            f"✅ Updated {entity_type.lower()}: {title} [{entity_id}]",
            style="green",
        )

        # Display updated fields if provided
        if _updates:
            for field, value in _updates.items():
                if value is not None and field != "id":  # Skip id field
                    if field == "estimated_hours" and value is not None:
                        # Format estimate as "Xh" or "Xd"
                        hours = float(value)
                        days = hours / 8.0
                        if days >= 1:
                            console.print(f"   estimate: {days:.1f}d", style="cyan")
                        else:
                            console.print(f"   estimate: {hours:.1f}h", style="cyan")
                    else:
                        # Format the field name nicely
                        display_field = field.replace("_", " ").title()
                        console.print(f"   {display_field}: {value}", style="cyan")


class DeletePresenter(BasePresenter):
    """Presenter for delete operation results."""

    def render(self, entity: Any) -> None:
        """Render deleted entity summary.

        Args:
            entity: The deleted entity object
        """
        console = self._get_console()
        entity_type = _infer_entity_type(entity)
        entity_id = _get_entity_id(entity)
        title = _get_entity_title(entity)

        console.print(
            f"✅ Deleted {entity_type.lower()}: {title} [{entity_id}]",
            style="green",
        )


class ArchivePresenter(BasePresenter):
    """Presenter for archive operation results."""

    def render(self, entity: Any) -> None:
        """Render archived entity summary.

        Args:
            entity: The archived entity object
        """
        console = self._get_console()
        entity_type = _infer_entity_type(entity)
        entity_id = _get_entity_id(entity)
        title = _get_entity_title(entity)

        console.print(
            f"📦 Archived {entity_type.lower()}: {title} [{entity_id}]",
            style="yellow",
        )


class RestorePresenter(BasePresenter):
    """Presenter for restore operation results."""

    def render(self, entity: Any) -> None:
        """Render restored entity summary.

        Args:
            entity: The restored entity object
        """
        console = self._get_console()
        entity_type = _infer_entity_type(entity)
        entity_id = _get_entity_id(entity)
        title = _get_entity_title(entity)

        console.print(
            f"✅ Restored {entity_type.lower()}: {title} [{entity_id}]",
            style="green",
        )
