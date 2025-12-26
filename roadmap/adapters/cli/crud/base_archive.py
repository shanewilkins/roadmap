"""Base class for archive operations across all entity types."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import click

from roadmap.adapters.cli.crud.crud_helpers import (
    EntityType,
    display_archive_success,
    get_active_dir,
    get_archive_dir,
)
from roadmap.common.console import get_console


class BaseArchive(ABC):
    """Abstract base class for entity archive commands using Template Method pattern.

    Subclasses must implement:
    - entity_type: The EntityType this archives
    - get_entities_to_archive(): Determine what entities to archive based on filters
    - post_archive_hook(): Update database and handle entity-specific logic

    Subclasses may override:
    - validate_entity_before_archive(): Custom validation before archiving
    - find_entity_files(): Custom file finding logic (default: filesystem search)

    This class handles the overall archive workflow:
    1. Determine entities to archive (via get_entities_to_archive)
    2. Find corresponding files
    3. Move files to archive
    4. Update state via post_archive_hook
    5. Display results
    """

    entity_type: EntityType

    def __init__(self, core: Any, console: Any = None) -> None:
        """Initialize archive command.

        Args:
            core: The core application context
            console: Optional console for output (uses default if not provided)
        """
        self.core = core
        self.console = console or get_console()

    @abstractmethod
    def get_entities_to_archive(
        self, entity_id: str | None = None, **filters
    ) -> list[Any]:
        """Determine which entities should be archived.

        Args:
            entity_id: Optional specific entity ID to archive
            **filters: Entity-specific filter criteria (e.g., all_closed, orphaned)

        Returns:
            List of entities to archive
        """

    @abstractmethod
    def post_archive_hook(
        self, archived_files: list[Path], entities: list[Any], **kwargs
    ) -> None:
        """Handle entity-specific state updates after archiving.

        Override to update database, send notifications, etc.

        Args:
            archived_files: List of files that were archived
            entities: List of entities that were archived
            **kwargs: Original CLI arguments
        """

    def validate_entity_before_archive(
        self, entity: Any, **kwargs
    ) -> tuple[bool, str | None]:
        """Optional validation before archiving an entity.

        Override to add entity-specific validation rules.

        Args:
            entity: The entity being considered for archive
            **kwargs: Original CLI arguments (e.g., force flag)

        Returns:
            Tuple of (is_valid, error_message_or_none)
        """
        return True, None

    def find_entity_files(self, entities: list[Any]) -> list[Path]:
        """Find file paths corresponding to entities.

        Override if entity-to-file mapping is non-standard.

        Args:
            entities: List of entities to find files for

        Returns:
            List of file paths
        """
        active_dir = get_active_dir(self.entity_type)
        files = []
        for entity in entities:
            # Search by entity ID prefix
            matching = list(active_dir.rglob(f"{str(entity.id)[:8]}*.md"))
            if matching:
                files.append(matching[0])
        return files

    def execute(self, entity_id: str | None = None, **kwargs) -> bool:
        """Execute archive operation (Template Method).

        Args:
            entity_id: Optional specific entity ID to archive
            **kwargs: Entity-specific filters and options

        Returns:
            True if archive succeeded
        """
        try:
            # Step 1: Determine which entities to archive
            entities = self.get_entities_to_archive(entity_id, **kwargs)

            if not entities:
                self.console.print(
                    f"No {self.entity_type.value}s to archive",
                    style="yellow",
                )
                return False

            # Step 2: Validate entities
            invalid_entities = []
            for entity in entities:
                is_valid, error_msg = self.validate_entity_before_archive(
                    entity, **kwargs
                )
                if not is_valid:
                    invalid_entities.append((entity, error_msg))

            if invalid_entities:
                for entity, error_msg in invalid_entities:
                    self.console.print(
                        f"⚠️  Cannot archive {entity.id}: {error_msg}",
                        style="yellow",
                    )
                # Continue with valid entities if any
                entities = [e for e in entities if (e, None) not in invalid_entities]
                if not entities:
                    return False

            # Step 3: Find corresponding files
            files_to_archive = self.find_entity_files(entities)

            if not files_to_archive:
                self.console.print(
                    f"Could not find files for {len(entities)} {self.entity_type.value}(s)",
                    style="yellow",
                )
                return False

            # Step 4: Move files to archive
            archive_dir = get_archive_dir(self.entity_type)
            archive_dir.mkdir(parents=True, exist_ok=True)

            archived_files = []
            failed_count = 0

            for file_path in files_to_archive:
                try:
                    archive_file = archive_dir / file_path.name
                    if archive_file.exists():
                        failed_count += 1
                        continue

                    archive_file.write_text(file_path.read_text())
                    file_path.unlink()
                    archived_files.append(archive_file)

                except Exception as e:
                    self.console.print(
                        f"⚠️  Failed to archive {file_path.name}: {str(e)}",
                        style="yellow",
                    )
                    failed_count += 1

            # Step 5: Update state via hook
            self.post_archive_hook(archived_files, entities, **kwargs)

            # Step 6: Display results
            display_archive_success(
                self.entity_type,
                len(archived_files),
                failed_count,
                console=self.console,
            )

            return True

        except Exception as e:
            self.console.print(
                f"❌ Archive operation failed: {str(e)}",
                style="red",
            )
            raise click.ClickException(str(e)) from e
