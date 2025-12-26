"""IssueRestore command implementation using base class."""

from pathlib import Path

from roadmap.adapters.cli.crud import BaseRestore, EntityType


class IssueRestore(BaseRestore):
    """Restore issue command implementation."""

    entity_type = EntityType.ISSUE

    def get_archived_files_to_restore(
        self, entity_id: str | None = None, **filters
    ) -> list[Path]:
        """Get archived issue files to restore.

        Args:
            entity_id: Specific issue ID to restore
            **filters: Additional filter criteria

        Returns:
            List of archived file paths
        """
        from roadmap.adapters.cli.crud.crud_helpers import get_archive_dir

        archive_dir = get_archive_dir(self.entity_type)

        if not archive_dir.exists():
            return []

        if entity_id:
            # Find specific issue file by ID prefix
            matching = list(archive_dir.rglob(f"{entity_id[:8]}*.md"))
            return matching if matching else []
        else:
            # Return all archived issues
            return list(archive_dir.rglob("*.md"))

    def post_restore_hook(self, restored_files: list[Path], **kwargs) -> None:
        """Handle post-restore state updates.

        Args:
            restored_files: Files that were restored
            **kwargs: Additional arguments
        """
        # Mark issues as restored in database
        for file_path in restored_files:
            try:
                # Extract issue ID from filename
                issue_id = file_path.stem.split("-")[0]
                self.core.db.mark_issue_archived(issue_id, archived=False)
            except Exception as e:
                self.console.print(
                    f"⚠️  Warning: Failed to update restoration status for {file_path.name}: {e}",
                    style="yellow",
                )
