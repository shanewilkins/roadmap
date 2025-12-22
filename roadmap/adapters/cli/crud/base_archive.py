"""Base class for archive operations across all entity types."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import click

from roadmap.adapters.cli.crud.crud_helpers import (
    EntityType,
    collect_archive_files,
    display_archive_success,
    get_active_dir,
    get_archive_dir,
)
from roadmap.common.console import get_console


class BaseArchive(ABC):
    """Abstract base class for entity archive commands.

    Subclasses implement:
    - entity_type: The EntityType this archives

    Handles moving entities to archive directory and updating state.
    Uses Template Method pattern for extensibility.
    """

    entity_type: EntityType

    def __init__(self, core: Any, console: Any = None) -> None:
        """Initialize archive command.

        Args:
            core: The core application context
            console: Optional console for output (uses default if not provided)
        """
        self.core = core
        self.console = console or get_console()

    @abstractmethod
    def post_archive_hook(self, archived_files: list[Path], **kwargs) -> None:
        """Optional hook after entities archived.

        Override to handle notifications, updates, etc.

        Args:
            archived_files: List of files that were archived
            **kwargs: Original CLI arguments
        """
        # Default: no-op. Subclasses override as needed.

    def execute(self, pattern: str | None = None, **kwargs) -> bool:
        """Execute archive operation.

        Args:
            pattern: Optional pattern to filter entities to archive
            **kwargs: All other CLI arguments

        Returns:
            True if archive succeeded
        """
        try:
            # Collect files matching pattern
            archived_files = []
            skipped_count = 0

            active_files = collect_archive_files(
                get_active_dir(self.entity_type), self.entity_type
            )

            if not active_files:
                self.console.print(
                    f"No {self.entity_type.value}s found to archive",
                    style="yellow",
                )
                return False

            # Filter by pattern if provided
            files_to_archive = active_files
            if pattern:
                files_to_archive = [
                    f for f in active_files if pattern.lower() in f.stem.lower()
                ]

            if not files_to_archive:
                self.console.print(
                    f"No {self.entity_type.value}s match pattern: {pattern}",
                    style="yellow",
                )
                return False

            # Archive each file
            archive_dir = get_archive_dir(self.entity_type)
            archive_dir.mkdir(parents=True, exist_ok=True)

            for file_path in files_to_archive:
                try:
                    # Check if already archived
                    archive_file = archive_dir / file_path.name
                    if archive_file.exists():
                        skipped_count += 1
                        continue

                    # Move to archive directory
                    archive_file.write_text(file_path.read_text())
                    file_path.unlink()
                    archived_files.append(archive_file)

                except Exception as e:
                    self.console.print(
                        f"⚠️  Failed to archive {file_path.name}: {str(e)}",
                        style="yellow",
                    )
                    skipped_count += 1
                    continue

            # Run post-archive hook
            self.post_archive_hook(archived_files, **kwargs)

            # Display results
            display_archive_success(
                self.entity_type,
                len(archived_files),
                skipped_count,
                console=self.console,
            )

            return True

        except Exception as e:
            self.console.print(
                f"❌ Archive operation failed: {str(e)}",
                style="red",
            )
            raise click.ClickException(str(e)) from e
