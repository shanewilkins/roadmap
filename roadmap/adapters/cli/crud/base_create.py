"""Base class for create operations across all entity types."""

from abc import ABC, abstractmethod
from typing import Any

from roadmap.adapters.cli.crud.crud_helpers import EntityType
from roadmap.adapters.cli.crud.crud_utils import (
    create_entity_by_type,
    get_entity_id,
    get_entity_title,
)
from roadmap.adapters.cli.presentation.crud_presenter import CreatePresenter
from roadmap.common.console import get_console
from roadmap.common.errors.exceptions import ValidationError
from roadmap.infrastructure.logging import log_audit_event


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
        ...

    def post_create_hook(self, entity: Any, **kwargs) -> None:  # noqa: B027
        """Optional hook after entity creation.

        Override to handle:
        - Git branch creation
        - Milestone assignments
        - Custom notifications

        Args:
            entity: The created entity
            **kwargs: Original CLI arguments
        """
        ...

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

            # Log audit event for successful creation
            entity_id = self._get_id(entity)
            log_audit_event(
                action="create",
                entity_type=self.entity_type.value,
                entity_id=entity_id,
                after=entity_dict,
            )

            # Display success
            self._display_success(entity)

            return entity

        except ValidationError:
            # ValidationError will be handled by centralized CLI exception handler
            # which formats it and directs to stderr
            raise
        except Exception:
            # Other exceptions will also be handled by centralized handler
            raise

    def _create_entity(self, entity_dict: dict[str, Any]) -> Any | None:
        """Create entity via appropriate service.

        Args:
            entity_dict: Dictionary of entity fields

        Returns:
            Created entity or None if failed
        """
        return create_entity_by_type(self.core, self.entity_type, entity_dict)

    def _display_success(self, entity: Any) -> None:
        """Display success message using presenter.

        Args:
            entity: The created entity
        """
        presenter = CreatePresenter()
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
