"""Base class for update operations across all entity types."""

from abc import ABC, abstractmethod
from typing import Any

import click

from roadmap.adapters.cli.crud.crud_helpers import EntityType
from roadmap.common.console import get_console
from roadmap.common.errors import ValidationError
from roadmap.infrastructure.logging import log_audit_event, log_validation_error


class BaseUpdate(ABC):
    """Abstract base class for entity update commands.

    Subclasses implement:
    - entity_type: The EntityType this updates
    - build_update_dict(): Convert CLI args to update dict
    - post_update_hook(): Optional hook after update (default: no-op)

    Uses Template Method pattern for extensibility.
    """

    entity_type: EntityType

    def __init__(self, core: Any, console: Any = None) -> None:
        """Initialize update command.

        Args:
            core: The core application context
            console: Optional console for output (uses default if not provided)
        """
        self.core = core
        self.console = console or get_console()

    @abstractmethod
    def build_update_dict(self, entity_id: str, **kwargs) -> dict[str, Any]:
        """Convert CLI arguments to update dictionary.

        Args:
            entity_id: ID of entity to update
            **kwargs: All click option values

        Returns:
            Dictionary of fields to update

        Raises:
            ValidationError: If arguments are invalid
        """
        pass

    def post_update_hook(
        self, entity: Any, update_dict: dict[str, Any], **kwargs
    ) -> None:
        """Optional hook after entity update.

        Override to handle:
        - Git branch updates
        - Milestone reassignments
        - Custom notifications

        Args:
            entity: The updated entity
            update_dict: The update dict that was applied
            **kwargs: Original CLI arguments
        """
        # Default: no-op. Subclasses override as needed.

    def execute(self, entity_id: str, **kwargs) -> Any | None:
        """Execute the update operation.

        Args:
            entity_id: ID of entity to update
            **kwargs: All other CLI arguments

        Returns:
            Updated entity, or None if update failed
        """
        try:
            # Verify entity exists
            entity = self._get_entity(entity_id)
            if entity is None:
                self.console.print(
                    f"❌ {self.entity_type.value.title()} '{entity_id}' not found",
                    style="red",
                )
                raise click.ClickException(f"{self.entity_type.value} not found")

            # Build update dict from arguments
            update_dict = self.build_update_dict(entity_id=entity_id, **kwargs)

            # Update via appropriate service
            updated_entity = self._update_entity(entity_id, update_dict)
            if updated_entity is None:
                return None

            # Run post-update hooks
            self.post_update_hook(updated_entity, update_dict, **kwargs)

            # Log audit event for successful update
            entity_id = self._get_id(updated_entity)
            log_audit_event(
                action="update",
                entity_type=self.entity_type.value,
                entity_id=entity_id,
                before={"entity_id": entity_id},  # Original only tracked by entity_id
                after=update_dict,
            )

            # Display success
            self._display_success(updated_entity)

            return updated_entity

        except ValidationError as e:
            # Log validation error with context
            log_validation_error(
                error=e,
                entity_type=self.entity_type.value,
                field_name=getattr(e, "field", None),
                proposed_value=getattr(e, "value", None),
            )
            self.console.print(f"❌ Validation error: {str(e)}", style="red")
            raise click.ClickException(str(e)) from e
        except Exception as e:
            self.console.print(
                f"❌ Failed to update {self.entity_type.value}: {str(e)}",
                style="red",
            )
            raise click.ClickException(str(e)) from e

    def _get_entity(self, entity_id: str) -> Any | None:
        """Get entity by ID.

        Args:
            entity_id: Entity ID to retrieve

        Returns:
            Entity object or None if not found
        """
        if self.entity_type == EntityType.ISSUE:
            return self.core.issues.get(entity_id)
        elif self.entity_type == EntityType.MILESTONE:
            return self.core.milestones.get(entity_id)
        elif self.entity_type == EntityType.PROJECT:
            return self.core.projects.get(entity_id)
        return None

    def _update_entity(self, entity_id: str, update_dict: dict[str, Any]) -> Any | None:
        """Update entity via appropriate service.

        Args:
            entity_id: Entity ID to update
            update_dict: Dictionary of fields to update

        Returns:
            Updated entity or None if failed
        """
        if self.entity_type == EntityType.ISSUE:
            return self.core.issues.update(entity_id, **update_dict)
        elif self.entity_type == EntityType.MILESTONE:
            return self.core.milestones.update(entity_id, **update_dict)
        elif self.entity_type == EntityType.PROJECT:
            return self.core.projects.update(entity_id, **update_dict)
        return None

    def _display_success(self, entity: Any) -> None:
        """Display success message.

        Args:
            entity: The updated entity
        """
        title = self._get_title(entity)
        entity_id = self._get_id(entity)

        self.console.print(
            f"✅ Updated {self.entity_type.value}: {title} [{entity_id}]",
            style="green",
        )

    def _get_title(self, entity: Any) -> str:
        """Get entity title/name.

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

    def _get_id(self, entity: Any) -> str:
        """Get entity ID.

        Args:
            entity: The entity object

        Returns:
            Entity ID string
        """
        return getattr(entity, "id", str(entity))
