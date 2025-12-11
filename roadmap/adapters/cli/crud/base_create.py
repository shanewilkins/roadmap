"""Base class for create operations across all entity types."""

from abc import ABC, abstractmethod
from typing import Any

import click

from roadmap.adapters.cli.crud.crud_helpers import EntityType
from roadmap.common.console import get_console
from roadmap.common.errors import ValidationError


class BaseCreate(ABC):
    """Abstract base class for entity creation commands.

    Subclasses implement:
    - entity_type: The EntityType this creates
    - build_entity_dict(): Convert CLI args to entity dict
    - post_create_hook(): Optional hook after creation (default: no-op)

    Uses Template Method pattern for extensibility.
    """

    entity_type: EntityType

    def __init__(self, core: Any, console: Any = None) -> None:
        """Initialize create command.

        Args:
            core: The core application context
            console: Optional console for output (uses default if not provided)
        """
        self.core = core
        self.console = console or get_console()

    @abstractmethod
    def build_entity_dict(self, **kwargs) -> dict[str, Any]:
        """Convert CLI arguments to entity dictionary.

        Args:
            **kwargs: All click option values

        Returns:
            Dictionary of entity fields to create

        Raises:
            ValidationError: If arguments are invalid
        """
        pass

    def post_create_hook(self, entity: Any, **kwargs) -> None:
        """Optional hook after entity creation.

        Override to handle:
        - Git branch creation
        - Milestone assignments
        - Custom notifications

        Args:
            entity: The created entity
            **kwargs: Original CLI arguments
        """
        # Default: no-op. Subclasses override as needed.

    def execute(self, title: str, **kwargs) -> Any | None:
        """Execute the create operation.

        Args:
            title: Entity title/name
            **kwargs: All other CLI arguments

        Returns:
            Created entity, or None if creation failed
        """
        try:
            # Build entity from arguments
            entity_dict = self.build_entity_dict(title=title, **kwargs)

            # Create via appropriate service
            entity = self._create_entity(entity_dict)
            if entity is None:
                return None

            # Run post-creation hooks
            self.post_create_hook(entity, **kwargs)

            # Display success
            self._display_success(entity)

            return entity

        except ValidationError as e:
            self.console.print(f"❌ Validation error: {str(e)}", style="red")
            raise click.ClickException(str(e)) from e
        except Exception as e:
            self.console.print(
                f"❌ Failed to create {self.entity_type.value}: {str(e)}",
                style="red",
            )
            raise click.ClickException(str(e)) from e

    def _create_entity(self, entity_dict: dict[str, Any]) -> Any | None:
        """Create entity via appropriate service.

        Args:
            entity_dict: Dictionary of entity fields

        Returns:
            Created entity or None if failed
        """
        if self.entity_type == EntityType.ISSUE:
            return self.core.issues.create(**entity_dict)
        elif self.entity_type == EntityType.MILESTONE:
            return self.core.milestones.create(**entity_dict)
        elif self.entity_type == EntityType.PROJECT:
            return self.core.projects.create(**entity_dict)
        return None

    def _display_success(self, entity: Any) -> None:
        """Display success message.

        Args:
            entity: The created entity
        """
        title = self._get_title(entity)
        entity_id = self._get_id(entity)

        self.console.print(
            f"✅ Created {self.entity_type.value}: {title} [{entity_id}]",
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
