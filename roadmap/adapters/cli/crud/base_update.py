"""Base class for update operations across all entity types."""

from abc import ABC, abstractmethod
from typing import Any

import click

from roadmap.adapters.cli.crud.crud_helpers import EntityType
from roadmap.adapters.cli.crud.crud_utils import (
    format_entity_not_found_error,
    get_entity_by_type,
    get_entity_id,
    get_entity_title,
    update_entity_by_type,
)
from roadmap.adapters.cli.presentation.crud_presenter import UpdatePresenter
from roadmap.common.console import get_console
from roadmap.common.errors.exceptions import ValidationError
from roadmap.common.logging import log_audit_event


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
        ...

    def post_update_hook(  # noqa: B027
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
        ...

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
                    format_entity_not_found_error(self.entity_type, entity_id),
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

        except ValidationError:
            # ValidationError will be handled by centralized CLI exception handler
            # which formats it and directs to stderr
            raise
        except Exception:
            # Other exceptions will also be handled by centralized handler
            raise

    def _get_entity(self, entity_id: str) -> Any | None:
        """Get entity by ID.

        Args:
            entity_id: Entity ID to retrieve

        Returns:
            Entity object or None if not found
        """
        return get_entity_by_type(self.core, self.entity_type, entity_id)

    def _update_entity(self, entity_id: str, update_dict: dict[str, Any]) -> Any | None:
        """Update entity via appropriate service.

        Args:
            entity_id: Entity ID to update
            update_dict: Dictionary of fields to update

        Returns:
            Updated entity or None if failed
        """
        return update_entity_by_type(
            self.core, self.entity_type, entity_id, update_dict
        )

    def _display_success(self, entity: Any) -> None:
        """Display success message.

        Args:
            entity: The updated entity
        """
        presenter = UpdatePresenter()
        presenter.render(entity)

    def _get_title(self, entity: Any) -> str:
        """Get entity title/name.

        Args:
            entity: The entity object

        Returns:
            Title or name string
        """
        return get_entity_title(entity)

    def _get_id(self, entity: Any) -> str:
        """Get entity ID.

        Args:
            entity: The entity object

        Returns:
            Entity ID string
        """
        return get_entity_id(entity)
