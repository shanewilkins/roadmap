"""ProjectRestore command implementation using base class."""

from pathlib import Path

from roadmap.adapters.cli.crud import BaseRestore, EntityType


class ProjectRestore(BaseRestore):
    """Restore project command implementation."""

    entity_type = EntityType.PROJECT

    def get_archived_files_to_restore(
        self, entity_id: str | None = None, **filters
    ) -> list[Path]:
        """Get archived project files to restore.

        Args:
            entity_id: Specific project ID to restore
            **filters: Additional filter criteria

        Returns:
            List of archived file paths
        """
        from roadmap.adapters.cli.crud.crud_helpers import get_archive_dir

        archive_dir = get_archive_dir(self.entity_type)

        if not archive_dir.exists():
            return []

        if entity_id:
            # Find specific project file by ID prefix
            matching = list(archive_dir.glob(f"{entity_id[:8]}*.md"))
            return matching if matching else []
        else:
            # Return all archived projects
            return list(archive_dir.glob("*.md"))

    def post_restore_hook(self, restored_files: list[Path], **kwargs) -> None:
        """Handle post-restore state updates.

        Args:
            restored_files: Files that were restored
            **kwargs: Additional arguments
        """
        for file_path in restored_files:
            try:
                # Extract project ID from filename
                project_id = file_path.stem.split("-")[0]
                self.core.db.mark_project_archived(project_id, archived=False)
            except Exception as e:
                self.console.print(
                    f"⚠️  Warning: Failed to update restoration status for {file_path.name}: {e}",
                    style="yellow",
                )
