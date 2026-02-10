"""MilestoneArchive command implementation using base class."""

import shutil
from pathlib import Path
from typing import Any

from roadmap.adapters.cli.crud import BaseArchive, EntityType
from roadmap.adapters.persistence.parser import MilestoneParser


class MilestoneArchive(BaseArchive):
    """Archive milestone command implementation."""

    entity_type = EntityType.MILESTONE

    def get_entities_to_archive(
        self, entity_id: str | None = None, all_closed: bool = False, **kwargs
    ) -> list[Any]:
        """Get milestones to archive based on criteria.

        Args:
            entity_id: Specific milestone name to archive
            all_closed: Archive all closed milestones
            **kwargs: Additional arguments

        Returns:
            List of milestones to archive
        """
        all_milestones = self.core.milestones.list()

        if entity_id:
            milestone = self.core.milestones.get(entity_id)
            return [milestone] if milestone else []
        elif all_closed:
            return [m for m in all_milestones if m.status.value == "closed"]

        return []

    def validate_entity_before_archive(
        self, entity: Any, **kwargs
    ) -> tuple[bool, str | None]:
        """Validate milestone before archiving.

        Args:
            entity: The milestone to validate
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
        """Find milestone files for entities.

        Args:
            entities: List of milestones

        Returns:
            List of file paths
        """
        roadmap_dir = Path.cwd() / ".roadmap"
        milestones_dir = roadmap_dir / "milestones"

        files = []
        for entity in entities:
            # Search for milestone file by name
            for md_file in milestones_dir.glob("*.md"):
                try:
                    milestone = MilestoneParser.parse_milestone_file(md_file)
                    if milestone.name == entity.name:
                        files.append(md_file)
                        break
                except Exception as e:
                    from roadmap.common.logging import get_logger

                    logger = get_logger(__name__)
                    logger.debug(
                        "milestone_parse_failed",
                        file=str(md_file),
                        error=str(e),
                        action="find_milestone_files",
                    )
                    continue
        return files

    def execute(self, entity_id: str | None = None, **kwargs) -> bool:
        """Execute archive operation.

        Archives milestones by moving files and setting the archived flag.

        Args:
            entity_id: Optional milestone name
            **kwargs: Filter options (all_closed, etc.)

        Returns:
            True if successful
        """
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
                is_valid, error_msg = self.validate_entity_before_archive(
                    entity, **kwargs
                )
                if not is_valid:
                    invalid_entities.append((entity, error_msg))
                    self.console.print(
                        f"⚠️  Cannot archive {entity.name}: {error_msg}",
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
                    archive_file = archive_dir / file_path.name
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

            # Update state (set archived flag and move associated issues)
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

        Moves associated issues folder and sets archived flag.

        Args:
            archived_files: Files that were archived
            entities: Entities that were archived
            **kwargs: Additional arguments
        """
        # Move associated issues folder to archive
        roadmap_dir = Path.cwd() / ".roadmap"

        for entity in entities:
            issues_dir = roadmap_dir / "issues" / entity.name
            if issues_dir.exists():
                archive_issues_dir = roadmap_dir / "archive" / "issues" / entity.name
                archive_issues_dir.parent.mkdir(parents=True, exist_ok=True)

                try:
                    shutil.move(str(issues_dir), str(archive_issues_dir))
                except Exception as e:
                    self.console.print(
                        f"⚠️  Warning: Failed to move issues for milestone {entity.name}: {e}",
                        style="yellow",
                    )

            # Set archived flag
            try:
                self.core.milestones.update_milestone(
                    name=entity.name,
                    archived=True,
                )
            except Exception as e:
                self.console.print(
                    f"⚠️  Warning: Failed to mark milestone {entity.name} as archived: {e}",
                    style="yellow",
                )
