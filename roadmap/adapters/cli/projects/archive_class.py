"""ProjectArchive command implementation using base class."""

from pathlib import Path
from typing import Any

from roadmap.adapters.cli.crud import BaseArchive, EntityType


class ProjectArchive(BaseArchive):
    """Archive project command implementation."""

    entity_type = EntityType.PROJECT

    def get_entities_to_archive(
        self, entity_id: str | None = None, **kwargs
    ) -> list[Any]:
        """Get projects to archive.

        Args:
            entity_id: Specific project ID to archive
            **kwargs: Additional arguments

        Returns:
            List of projects to archive
        """
        if entity_id:
            project = self.core.projects.get(entity_id)
            return [project] if project else []

        return []

    def validate_entity_before_archive(
        self, entity: Any, **kwargs
    ) -> tuple[bool, str | None]:
        """Validate project before archiving.

        Args:
            entity: The project to validate
            **kwargs: Additional arguments (e.g., force flag)

        Returns:
            Tuple of (is_valid, error_message)
        """
        return True, None

    def find_entity_files(self, entities: list[Any]) -> list[Path]:
        """Find project files for entities.

        Args:
            entities: List of projects

        Returns:
            List of file paths
        """
        roadmap_dir = Path.cwd() / ".roadmap"
        projects_dir = roadmap_dir / "projects"

        files = []
        for entity in entities:
            # Search for project file by ID prefix
            matching = list(projects_dir.glob(f"{str(entity.id)[:8]}*.md"))
            if matching:
                files.append(matching[0])
        return files

    def post_archive_hook(
        self, archived_files: list[Path], entities: list[Any], **kwargs
    ) -> None:
        """Handle post-archive state updates.

        Args:
            archived_files: Files that were archived
            entities: Entities that were archived
            **kwargs: Additional arguments
        """
        for entity in entities:
            try:
                self.core.db.mark_project_archived(entity.id, archived=True)
            except Exception as e:
                self.console.print(
                    f"⚠️  Warning: Failed to mark project {entity.id} as archived: {e}",
                    style="yellow",
                )
