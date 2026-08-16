"""IssueArchive command implementation using base class."""

from pathlib import Path
from typing import Any

from roadmap.adapters.cli.crud import BaseArchive, EntityType


class IssueArchive(BaseArchive):
    """Archive issue command implementation."""

    entity_type = EntityType.ISSUE

    def get_entities_to_archive(
        self,
        entity_id: str | None = None,
        all_closed: bool = False,
        orphaned: bool = False,
        **kwargs,
    ) -> list[Any]:
        """Get issues to archive based on criteria.

        Args:
            entity_id: Specific issue ID to archive
            all_closed: Archive all closed issues
            orphaned: Archive issues with no milestone
            **kwargs: Additional arguments

        Returns:
            List of issues to archive
        """
        all_issues = self.core.issues.list()

        if entity_id:
            issue = self.core.issues.get(entity_id)
            return [issue] if issue else []
        elif all_closed:
            return [i for i in all_issues if i.status.value == "closed"]
        elif orphaned:
            return [i for i in all_issues if not i.milestone]

        return []

    def validate_entity_before_archive(
        self, entity: Any, **kwargs
    ) -> tuple[bool, str | None]:
        """Validate issue before archiving.

        Args:
            entity: The issue to validate
            **kwargs: Additional arguments (e.g., force flag)

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Allow archiving if force flag is set
        if kwargs.get("force"):
            return True, None

        if entity.status.value != "closed":
            return False, f"not closed (status: {entity.status.value})"
        return True, None

    def find_entity_files(self, entities: list[Any]) -> list[Path]:
        """Find issue files for entities.

        Args:
            entities: List of issues

        Returns:
            List of file paths
        """
        roadmap_dir = Path.cwd() / ".roadmap"
        issues_dir = roadmap_dir / "issues"

        files = []
        for entity in entities:
            # Search recursively for issue file by ID prefix
            matching = list(issues_dir.rglob(f"{str(entity.id)[:8]}*.md"))
            if matching:
                files.append(matching[0])
        return files

    def get_archive_path(self, archive_dir: Path, issue_file: Path) -> Path:
        """Determine archive path preserving folder structure.

        Args:
            archive_dir: The archive root directory
            issue_file: The issue file path

        Returns:
            The destination path for archiving
        """
        roadmap_dir = Path.cwd() / ".roadmap"
        issues_dir = roadmap_dir / "issues"

        try:
            rel_path = issue_file.relative_to(issues_dir)
        except ValueError as e:
            from roadmap.common.logging import get_logger

            logger = get_logger(__name__)
            logger.debug(
                "issue_relative_path_failed",
                file=str(issue_file),
                error=str(e),
                action="calculate_archive_path",
            )
            return archive_dir / issue_file.name

        # If file is directly in issues_dir (no parent folder), put in archive root
        if len(rel_path.parts) == 1:
            return archive_dir / issue_file.name

        # Preserve the parent folder structure
        dest_dir = archive_dir / rel_path.parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        return dest_dir / issue_file.name

    def pre_archive_hook(self, entities: list[Any], **kwargs) -> None:
        """Bring the local SQLite projection current before moving files."""
        stats = self.core.db.sync_directory_incremental(Path.cwd() / ".roadmap")
        if stats.get("files_failed"):
            raise RuntimeError("Failed to sync local issue state before archiving")

    def post_archive_hook(
        self, archived_files: list[Path], entities: list[Any], **kwargs
    ) -> None:
        """Handle post-archive state updates.

        Sets the archived flag on entities after moving files.

        Args:
            archived_files: Files that were archived
            entities: Entities that were archived
            **kwargs: Additional arguments
        """
        from roadmap.adapters.persistence.parser import IssueParser

        for archived_file in archived_files:
            issue = IssueParser.parse_issue_file(archived_file)
            if self.core.issues.update(issue.id, archived=True) is None:
                raise RuntimeError(f"Failed to archive issue {issue.id}")
            if not self.core.db.mark_issue_archived(issue.id):
                raise RuntimeError(f"Failed to update issue projection {issue.id}")
