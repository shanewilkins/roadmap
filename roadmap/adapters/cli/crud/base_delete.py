"""Base class for delete operations across all entity types."""

from abc import ABC
from typing import Any

import click

from roadmap.adapters.cli.crud.crud_helpers import EntityType
from roadmap.adapters.cli.crud.crud_utils import (
    delete_entity_by_type,
    format_entity_not_found_error,
    get_entity_by_type,
    get_entity_title,
)
from roadmap.adapters.cli.presentation.crud_presenter import DeletePresenter
from roadmap.common.console import get_console


class BaseDelete(ABC):
    """Abstract base class for entity delete commands.

    Subclasses implement:
    - entity_type: The EntityType this deletes

    Uses Template Method pattern for extensibility.
    """

    entity_type: EntityType

    def __init__(self, core: Any, console: Any = None) -> None:
        """Initialize delete command.

        Args:
            core: The core application context
            console: Optional console for output (uses default if not provided)
        """
        self.core = core
        self.console = console or get_console()

    def post_delete_hook(self, entity_id: str, **kwargs) -> None:  # noqa: B027
        """Optional hook after entity deletion.

        Override to handle cleanup, notifications, etc.

        Args:
            entity_id: ID of deleted entity
            **kwargs: Original CLI arguments
        """
        pass

    def execute(self, entity_id: str, force: bool = False, **kwargs) -> bool:
        """Execute the delete operation.

        Args:
            entity_id: ID of entity to delete
            force: Whether to force deletion without confirmation
            **kwargs: All other CLI arguments

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            # Verify entity exists
            entity = self._get_entity(entity_id)
            if entity is None:
                self.console.print(
                    format_entity_not_found_error(self.entity_type, entity_id),
                    style="red",
                )
                return False

            # Request confirmation if not forced
            if not force:
                title = self._get_title(entity)
                if not click.confirm(
                    f"Delete {self.entity_type.value} '{title}'? This cannot be undone."
                ):
                    self.console.print("⚠️  Delete cancelled", style="yellow")
                    return False

            # Delete via appropriate service
            if not self._delete_entity(entity_id):
                return False

            # Run post-delete hooks
            self.post_delete_hook(entity_id, **kwargs)

            # Display success
            self._display_success(entity_id, entity)

            return True

        except Exception as e:
            self.console.print(
                f"❌ Failed to delete {self.entity_type.value}: {str(e)}",
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
        return get_entity_by_type(self.core, self.entity_type, entity_id)

    def _delete_entity(self, entity_id: str) -> bool:
        """Delete entity via appropriate service.

        Args:
            entity_id: Entity ID to delete

        Returns:
            True if deletion succeeded
        """
        try:
            delete_entity_by_type(self.core, self.entity_type, entity_id)
            return True
        except Exception:
            return False

    def _display_success(self, entity_id: str, entity: Any) -> None:
        """Display success message.

        Args:
            entity_id: ID of deleted entity
            entity: The deleted entity
        """
        presenter = DeletePresenter()
        presenter.render(entity)

    def _get_title(self, entity: Any) -> str:
        """Get entity title/name.

        Args:
            entity: The entity object

        Returns:
            Title or name string
        """
        return get_entity_title(entity)
