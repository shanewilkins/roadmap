"""Base class for restore operations across all entity types."""

from abc import ABC
from pathlib import Path
from typing import Any

import click

from roadmap.adapters.cli.crud.crud_helpers import (
    EntityType,
    collect_archive_files,
    display_restore_success,
    get_active_dir,
    get_archive_dir,
)
from roadmap.common.console import get_console


class BaseRestore(ABC):
    """Abstract base class for entity restore commands.

    Subclasses implement:
    - entity_type: The EntityType this restores

    Handles moving entities from archive back to active directory.
    Uses Template Method pattern for extensibility.
    """

    entity_type: EntityType

    def __init__(self, core: Any, console: Any = None) -> None:
        """Initialize restore command.

        Args:
            core: The core application context
            console: Optional console for output (uses default if not provided)
        """
        self.core = core
        self.console = console or get_console()

    def post_restore_hook(self, restored_files: list[Path], **kwargs) -> None:
        """Optional hook after entities restored.

        Override to handle notifications, updates, etc.

        Args:
            restored_files: List of files that were restored
            **kwargs: Original CLI arguments
        """
        # Default: no-op. Subclasses override as needed.

    def execute(self, pattern: str | None = None, **kwargs) -> bool:
        """Execute restore operation.

        Args:
            pattern: Optional pattern to filter entities to restore
            **kwargs: All other CLI arguments

        Returns:
            True if restore succeeded
        """
        try:
            # Collect archived files
            archive_dir = get_archive_dir(self.entity_type)

            if not archive_dir.exists():
                self.console.print(
                    f"No archive found for {self.entity_type.value}s",
                    style="yellow",
                )
                return False

            archived_files = collect_archive_files(archive_dir, self.entity_type)

            if not archived_files:
                self.console.print(
                    f"No archived {self.entity_type.value}s found",
                    style="yellow",
                )
                return False

            # Filter by pattern if provided
            files_to_restore = archived_files
            if pattern:
                files_to_restore = [
                    f for f in archived_files if pattern.lower() in f.stem.lower()
                ]

            if not files_to_restore:
                self.console.print(
                    f"No archived {self.entity_type.value}s match pattern: {pattern}",
                    style="yellow",
                )
                return False

            # Restore each file
            active_dir = get_active_dir(self.entity_type)
            active_dir.mkdir(parents=True, exist_ok=True)

            restored_files = []
            failed_count = 0

            for archive_file in files_to_restore:
                try:
                    # Check if already active (conflict)
                    active_file = active_dir / archive_file.name
                    if active_file.exists():
                        self.console.print(
                            f"⚠️  Cannot restore {archive_file.name}: already exists in active",
                            style="yellow",
                        )
                        failed_count += 1
                        continue

                    # Restore from archive
                    active_file.write_text(archive_file.read_text())
                    archive_file.unlink()
                    restored_files.append(active_file)

                except Exception as e:
                    self.console.print(
                        f"⚠️  Failed to restore {archive_file.name}: {str(e)}",
                        style="yellow",
                    )
                    failed_count += 1
                    continue

            # Run post-restore hook
            self.post_restore_hook(restored_files, **kwargs)

            # Display results
            display_restore_success(
                self.entity_type,
                len(restored_files),
                failed_count,
                console=self.console,
            )

            return True

        except Exception as e:
            self.console.print(
                f"❌ Restore operation failed: {str(e)}",
                style="red",
            )
            raise click.ClickException(str(e)) from e
