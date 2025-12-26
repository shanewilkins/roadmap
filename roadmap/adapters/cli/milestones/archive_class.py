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
                except Exception:
                    continue
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

            # Update database
            try:
                self.core.db.mark_milestone_archived(entity.name, archived=True)
            except Exception as e:
                self.console.print(
                    f"⚠️  Warning: Failed to mark milestone {entity.name} as archived: {e}",
                    style="yellow",
                )
