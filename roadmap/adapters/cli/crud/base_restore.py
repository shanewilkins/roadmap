"""Base class for restore operations across all entity types."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import click

from roadmap.adapters.cli.crud.crud_helpers import (
    EntityType,
    display_restore_success,
    get_active_dir,
    get_archive_dir,
)
from roadmap.common.console import get_console


class BaseRestore(ABC):
    """Abstract base class for entity restore commands using Template Method pattern.

    Subclasses must implement:
    - entity_type: The EntityType this restores
    - get_archived_files_to_restore(): Determine which archived files to restore
    - post_restore_hook(): Update database and handle entity-specific logic

    Subclasses may override:
    - validate_entity_before_restore(): Custom validation before restoring
    - check_conflict(): Custom conflict detection logic

    This class handles the overall restore workflow:
    1. Find archived files matching criteria
    2. Validate before restoring
    3. Check for conflicts with active entities
    4. Move files from archive to active
    5. Update state via post_restore_hook
    6. Display results
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

    @abstractmethod
    def get_archived_files_to_restore(
        self, entity_id: str | None = None, **filters
    ) -> list[Path]:
        """Determine which archived files should be restored.

        Args:
            entity_id: Optional specific entity ID to restore
            **filters: Entity-specific filter criteria

        Returns:
            List of archived file paths to restore
        """

    @abstractmethod
    def post_restore_hook(self, restored_files: list[Path], **kwargs) -> None:
        """Handle entity-specific state updates after restoring.

        Override to update database, send notifications, etc.

        Args:
            restored_files: List of files that were restored
            **kwargs: Original CLI arguments
        """

    def validate_entity_before_restore(
        self, file_path: Path
    ) -> tuple[bool, str | None]:
        """Optional validation before restoring an entity.

        Override to add entity-specific validation rules.

        Args:
            file_path: The file being considered for restore

        Returns:
            Tuple of (is_valid, error_message_or_none)
        """
        return True, None

    def check_conflict(self, archived_file: Path) -> tuple[bool, str | None]:
        """Check if restoring would cause a conflict.

        Override for custom conflict detection.

        Args:
            archived_file: The file being restored

        Returns:
            Tuple of (has_conflict, conflict_description)
        """
        active_dir = get_active_dir(self.entity_type)
        active_file = active_dir / archived_file.name
        if active_file.exists():
            return True, f"already exists in active {self.entity_type.value}s"
        return False, None

    def _validate_files_for_restore(
        self, files_to_restore: list[Path]
    ) -> tuple[list[Path], list[tuple[Path, str | None]]]:
        """Validate files before restoration.

        Args:
            files_to_restore: List of files to validate

        Returns:
            Tuple of (valid_files, invalid_files_with_reasons)
        """
        invalid_files = []

        for file_path in files_to_restore:
            is_valid, error_msg = self.validate_entity_before_restore(file_path)
            if not is_valid:
                invalid_files.append((file_path, error_msg))

        valid_files = [
            f for f in files_to_restore if f not in [f[0] for f in invalid_files]
        ]

        return valid_files, invalid_files

    def _check_files_for_conflicts(
        self, files_to_restore: list[Path]
    ) -> tuple[list[Path], list[tuple[Path, str | None]]]:
        """Check files for conflicts with active entities.

        Args:
            files_to_restore: List of files to check

        Returns:
            Tuple of (non_conflicting_files, conflicting_files_with_reasons)
        """
        conflicts = []

        for file_path in files_to_restore:
            has_conflict, conflict_desc = self.check_conflict(file_path)
            if has_conflict:
                conflicts.append((file_path, conflict_desc))

        non_conflicting = [
            f for f in files_to_restore if f not in [f[0] for f in conflicts]
        ]

        return non_conflicting, conflicts

    def _perform_file_restore(
        self, files_to_restore: list[Path]
    ) -> tuple[list[Path], int]:
        """Move files from archive to active directory.

        Args:
            files_to_restore: List of files to restore

        Returns:
            Tuple of (successfully_restored_files, failed_count)
        """
        active_dir = get_active_dir(self.entity_type)
        active_dir.mkdir(parents=True, exist_ok=True)

        restored_files = []
        failed_count = 0

        for archive_file in files_to_restore:
            try:
                active_file = active_dir / archive_file.name
                active_file.write_text(archive_file.read_text())
                archive_file.unlink()
                restored_files.append(active_file)
            except Exception as e:
                self.console.print(
                    f"⚠️  Failed to restore {archive_file.name}: {str(e)}",
                    style="yellow",
                )
                failed_count += 1

        return restored_files, failed_count

    def _display_validation_errors(
        self, invalid_files: list[tuple[Path, str | None]]
    ) -> None:
        """Display validation errors to user.

        Args:
            invalid_files: List of files with validation errors
        """
        for file_path, error_msg in invalid_files:
            self.console.print(
                f"⚠️  Cannot restore {file_path.name}: {error_msg}",
                style="yellow",
            )

    def _display_conflicts(self, conflicts: list[tuple[Path, str | None]]) -> None:
        """Display conflict errors to user.

        Args:
            conflicts: List of conflicting files
        """
        for file_path, conflict_desc in conflicts:
            self.console.print(
                f"⚠️  Cannot restore {file_path.name}: {conflict_desc}",
                style="yellow",
            )

    def execute(self, entity_id: str | None = None, **kwargs) -> bool:
        """Execute restore operation (Template Method).

        Args:
            entity_id: Optional specific entity ID to restore
            **kwargs: Entity-specific filters and options

        Returns:
            True if restore succeeded
        """
        try:
            # Step 1: Find archived files matching criteria
            archive_dir = get_archive_dir(self.entity_type)

            if not archive_dir.exists():
                self.console.print(
                    f"No archive found for {self.entity_type.value}s",
                    style="yellow",
                )
                return False

            files_to_restore = self.get_archived_files_to_restore(entity_id, **kwargs)

            if not files_to_restore:
                self.console.print(
                    f"No archived {self.entity_type.value}s found to restore",
                    style="yellow",
                )
                return False

            # Step 2: Validate files
            files_to_restore, invalid_files = self._validate_files_for_restore(
                files_to_restore
            )
            if invalid_files:
                self._display_validation_errors(invalid_files)
                if not files_to_restore:
                    return False

            # Step 3: Check for conflicts
            files_to_restore, conflicts = self._check_files_for_conflicts(
                files_to_restore
            )
            if conflicts:
                self._display_conflicts(conflicts)
                if not files_to_restore:
                    return False

            # Step 4: Restore files
            restored_files, failed_count = self._perform_file_restore(files_to_restore)

            # Step 5: Update state via hook
            self.post_restore_hook(restored_files, **kwargs)

            # Step 6: Display results
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
