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
        from pathlib import Path

        roadmap_dir = Path.cwd() / ".roadmap"
        issues_dir = roadmap_dir / "issues"

        files = []
        for entity in entities:
            # Search recursively for issue file by ID prefix
            matching = list(issues_dir.rglob(f"{str(entity.id)[:8]}*.md"))
            if matching:
                files.append(matching[0])
        return files

    def _determine_archive_path(self, archive_dir: Path, issue_file: Path) -> Path:
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
        except ValueError:
            # File is not under issues_dir, put in root
            return archive_dir / issue_file.name

        # If file is directly in issues_dir (no parent folder), put in archive root
        if len(rel_path.parts) == 1:
            return archive_dir / issue_file.name

        # Preserve the parent folder structure
        dest_dir = archive_dir / rel_path.parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        return dest_dir / issue_file.name

    def execute(self, entity_id: str | None = None, **kwargs) -> bool:
        """Execute archive operation.

        Args:
            entity_id: Optional issue ID
            **kwargs: Filter options (all_closed, orphaned, etc.)

        Returns:
            True if successful
        """
        # Call parent execute, but override file movement to use preserve-folder logic
        try:
            entities = self.get_entities_to_archive(entity_id, **kwargs)

            if not entities:
                self.console.print(
                    f"No {self.entity_type.value}s to archive",
                    style="yellow",
                )
                return False

            # Validate entities
            invalid_entities = []
            for entity in entities:
                is_valid, error_msg = self.validate_entity_before_archive(entity)
                if not is_valid:
                    invalid_entities.append((entity, error_msg))
                    self.console.print(
                        f"⚠️  Cannot archive {entity.id}: {error_msg}",
                        style="yellow",
                    )

            if invalid_entities:
                entities = [e for e in entities if (e, None) not in invalid_entities]
                if not entities:
                    return False

            # Find files
            files_to_archive = self.find_entity_files(entities)

            if not files_to_archive:
                self.console.print(
                    f"Could not find files for {len(entities)} {self.entity_type.value}(s)",
                    style="yellow",
                )
                return False

            # Archive with folder structure preservation
            from roadmap.adapters.cli.crud.crud_helpers import (
                display_archive_success,
                get_archive_dir,
            )

            archive_dir = get_archive_dir(self.entity_type)
            archive_dir.mkdir(parents=True, exist_ok=True)

            archived_files = []
            failed_count = 0

            for file_path in files_to_archive:
                try:
                    archive_file = self._determine_archive_path(archive_dir, file_path)
                    if archive_file.exists():
                        failed_count += 1
                        continue

                    # Ensure parent directory exists and use rename (mv) for atomicity
                    archive_file.parent.mkdir(parents=True, exist_ok=True)
                    file_path.rename(archive_file)
                    archived_files.append(archive_file)

                except Exception as e:
                    self.console.print(
                        f"⚠️  Failed to archive {file_path.name}: {str(e)}",
                        style="yellow",
                    )
                    failed_count += 1

            # Update state
            self.post_archive_hook(archived_files, entities, **kwargs)

            # Display results
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
            import click

            raise click.ClickException(str(e)) from e

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
                self.core.db.mark_issue_archived(entity.id, archived=True)
            except Exception as e:
                self.console.print(
                    f"⚠️  Warning: Failed to mark issue {entity.id} as archived: {e}",
                    style="yellow",
                )

        # Clear the list cache after archiving to ensure archived issues don't appear in list output
        self.core.issues._ops.issue_service._list_issues_cache.clear()
