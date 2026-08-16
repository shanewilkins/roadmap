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
        from roadmap.adapters.persistence.parser import IssueParser

        issue_ids = []
        for file_path in restored_files:
            issue = IssueParser.parse_issue_file(file_path)
            updates = {"archived": False}
            if kwargs.get("status"):
                updates["status"] = kwargs["status"]
            if self.core.issues.update(issue.id, **updates) is None:
                raise RuntimeError(f"Failed to restore issue {issue.id}")
            issue_ids.append(issue.id)

        stats = self.core.db.sync_directory_incremental(Path.cwd() / ".roadmap")
        if stats.get("files_failed"):
            raise RuntimeError("Failed to sync local issue state after restoring")
        for issue_id in issue_ids:
            if not self.core.db.mark_issue_archived(issue_id, archived=False):
                raise RuntimeError(f"Failed to update issue projection {issue_id}")
