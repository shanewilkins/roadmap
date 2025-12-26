"""MilestoneRestore command implementation using base class."""

import shutil
from pathlib import Path

from roadmap.adapters.cli.crud import BaseRestore, EntityType
from roadmap.adapters.persistence.parser import MilestoneParser


class MilestoneRestore(BaseRestore):
    """Restore milestone command implementation."""

    entity_type = EntityType.MILESTONE

    def get_archived_files_to_restore(
        self, entity_id: str | None = None, **filters
    ) -> list[Path]:
        """Get archived milestone files to restore.

        Args:
            entity_id: Specific milestone name to restore
            **filters: Additional filter criteria

        Returns:
            List of archived file paths
        """
        from roadmap.adapters.cli.crud.crud_helpers import get_archive_dir

        archive_dir = get_archive_dir(self.entity_type)

        if not archive_dir.exists():
            return []

        if entity_id:
            # Find specific milestone file by name
            for md_file in archive_dir.glob("*.md"):
                try:
                    milestone = MilestoneParser.parse_milestone_file(md_file)
                    if milestone.name == entity_id:
                        return [md_file]
                except Exception:
                    continue
            return []
        else:
            # Return all archived milestones
            return list(archive_dir.glob("*.md"))

    def post_restore_hook(self, restored_files: list[Path], **kwargs) -> None:
        """Handle post-restore state updates.

        Args:
            restored_files: Files that were restored
            **kwargs: Additional arguments
        """
        # Move associated issues folder back from archive
        roadmap_dir = Path.cwd() / ".roadmap"

        for file_path in restored_files:
            try:
                milestone = MilestoneParser.parse_milestone_file(file_path)
                milestone_name = milestone.name

                archive_issues_dir = roadmap_dir / "archive" / "issues" / milestone_name
                if archive_issues_dir.exists():
                    active_issues_dir = roadmap_dir / "issues" / milestone_name
                    active_issues_dir.parent.mkdir(parents=True, exist_ok=True)

                    try:
                        shutil.move(str(archive_issues_dir), str(active_issues_dir))
                    except Exception as e:
                        self.console.print(
                            f"⚠️  Warning: Failed to restore issues for milestone {milestone_name}: {e}",
                            style="yellow",
                        )

                # Update database
                try:
                    self.core.db.mark_milestone_archived(milestone_name, archived=False)
                except Exception as e:
                    self.console.print(
                        f"⚠️  Warning: Failed to update restoration status for {milestone_name}: {e}",
                        style="yellow",
                    )
            except Exception as e:
                self.console.print(
                    f"⚠️  Failed to process milestone file {file_path.name}: {e}",
                    style="yellow",
                )
