"""Specialized synchronizers for different entity types."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from roadmap.adapters.persistence.file_parser import FileParser
from roadmap.common.datetime_parser import UnifiedDateTimeParser
from roadmap.common.logging import get_logger
from roadmap.core.interfaces.sync_validators import (
    ForeignKeyValidationError,
    ForeignKeyValidator,
)

logger = get_logger(__name__)


class EntitySyncCoordinator:
    """Base coordinator for syncing entity files to database."""

    def __init__(self, get_connection, transaction_context):
        """Initialize the coordinator.

        Args:
            get_connection: Callable that returns a database connection
            transaction_context: Context manager for transactions
        """
        self._get_connection = get_connection
        self._transaction = transaction_context
        self._parser = FileParser()

    def _get_default_project_id(self) -> str | None:
        """Get the first available project ID for orphaned items."""
        try:
            with self._transaction() as conn:
                result = conn.execute("SELECT id FROM projects LIMIT 1").fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(
                "failed_to_get_default_project_id", error=str(e), severity="operational"
            )
            return None

    def _get_milestone_id_by_name(self, milestone_name: str) -> str | None:
        """Get milestone ID by name."""
        try:
            with self._transaction() as conn:
                result = conn.execute(
                    "SELECT id FROM milestones WHERE title = ?", (milestone_name,)
                ).fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.warning(
                "failed_to_find_milestone",
                milestone_name=milestone_name,
                error=str(e),
                severity="operational",
            )
            return None

    def _normalize_date(self, date_value: Any) -> Any:
        """Normalize date field from YAML."""
        if not date_value:
            return None
        try:
            if isinstance(date_value, str):
                dt = UnifiedDateTimeParser.parse_any_datetime(date_value)
                return dt.date() if dt else None
            return date_value
        except (ValueError, AttributeError):
            return None

    def _extract_metadata(self, data: dict, exclude_fields: list[str]) -> str | None:
        """Extract non-standard fields as JSON metadata."""
        metadata = {k: v for k, v in data.items() if k not in exclude_fields}
        if not metadata:
            return None

        return json.dumps(metadata, default=self._json_default)

    @staticmethod
    def _json_default(value: Any) -> str:
        """Handle JSON serialization of non-standard types."""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        # Handle datetime-like objects that may have isoformat method
        if hasattr(value, "isoformat") and callable(value.isoformat):
            try:
                result = value.isoformat()
                if isinstance(result, str):
                    return result
            except Exception:
                pass
        raise TypeError(
            f"Object of type {type(value).__name__} is not JSON serializable"
        )

    def _update_sync_status(self, file_path: Path) -> None:
        """Update sync status for a file."""
        metadata = self._parser.extract_file_metadata(file_path)
        if metadata:
            with self._transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO file_sync_state
                    (file_path, content_hash, file_size, last_modified)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        str(file_path),
                        metadata["hash"],
                        metadata["size"],
                        metadata["modified_time"],
                    ),
                )


class MilestoneFKValidator(ForeignKeyValidator):
    """Validates foreign key constraints for milestone syncing.

    Ensures that projects table has data before syncing milestones,
    preventing FOREIGN KEY constraint violations.
    """

    def __init__(self, get_connection):
        """Initialize validator.

        Args:
            get_connection: Callable that returns database connection
        """
        self._get_connection = get_connection

    def validate(self) -> None:
        """Validate that projects table has data.

        Raises:
            ForeignKeyValidationError: If projects table is empty
            RuntimeError: If database connection fails
        """
        try:
            with self._get_connection() as conn:
                result = conn.execute(
                    "SELECT COUNT(*) as count FROM projects"
                ).fetchone()
                project_count = result[0] if result else 0

                if project_count == 0:
                    raise ForeignKeyValidationError(
                        entity_type="milestone",
                        missing_references=[],
                        error_details="Projects table is empty. Cannot sync milestones without prerequisite projects. "
                        "Ensure ProjectSyncCoordinator syncs all projects before MilestoneSyncCoordinator.",
                    )

                logger.info(
                    "milestone_fk_validation_passed",
                    project_count=project_count,
                )

        except ForeignKeyValidationError:
            raise
        except Exception as e:
            logger.error(
                "milestone_fk_validation_error",
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
            raise RuntimeError(
                f"Failed to validate milestone FK constraints: {str(e)}"
            ) from e

    def missing_prerequisites(self) -> list[str]:
        """Return list of empty prerequisite tables.

        Returns:
            List describing which prerequisites are missing
        """
        try:
            with self._get_connection() as conn:
                result = conn.execute(
                    "SELECT COUNT(*) as count FROM projects"
                ).fetchone()
                project_count = result[0] if result else 0

                if project_count == 0:
                    return ["projects (empty)"]
                return []

        except Exception as e:
            logger.error("Error checking prerequisites", error=str(e))
            return ["unknown (database error)"]


class IssueFKValidator(ForeignKeyValidator):
    """Validates foreign key constraints for issue syncing.

    Ensures that both projects and milestones tables have prerequisite data
    before syncing issues, preventing FOREIGN KEY constraint violations.
    """

    def __init__(self, get_connection):
        """Initialize validator.

        Args:
            get_connection: Callable that returns database connection
        """
        self._get_connection = get_connection

    def validate(self) -> None:
        """Validate that projects table has data.

        Raises:
            ForeignKeyValidationError: If projects table is empty
            RuntimeError: If database connection fails

        Notes:
            Issues depend on projects being populated.
            Milestones are optional but must exist if referenced.
        """
        try:
            with self._get_connection() as conn:
                # Check projects (required)
                projects_result = conn.execute(
                    "SELECT COUNT(*) as count FROM projects"
                ).fetchone()
                project_count = projects_result[0] if projects_result else 0

                if project_count == 0:
                    raise ForeignKeyValidationError(
                        entity_type="issue",
                        missing_references=[],
                        error_details="Projects table is empty. Cannot sync issues without prerequisite projects. "
                        "Ensure ProjectSyncCoordinator syncs all projects before IssueSyncCoordinator.",
                    )

                logger.info(
                    "issue_fk_validation_passed",
                    project_count=project_count,
                )

        except ForeignKeyValidationError:
            raise
        except Exception as e:
            logger.error(
                "issue_fk_validation_error",
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
            raise RuntimeError(
                f"Failed to validate issue FK constraints: {str(e)}"
            ) from e

    def missing_prerequisites(self) -> list[str]:
        """Return list of empty prerequisite tables.

        Returns:
            List describing which prerequisites are missing
        """
        try:
            with self._get_connection() as conn:
                result = conn.execute(
                    "SELECT COUNT(*) as count FROM projects"
                ).fetchone()
                project_count = result[0] if result else 0

                if project_count == 0:
                    return ["projects (empty)"]
                return []

        except Exception as e:
            logger.error("Error checking prerequisites", error=str(e))
            return ["unknown (database error)"]


class IssueSyncCoordinator(EntitySyncCoordinator):
    """Handles syncing issue files to database."""

    def _extract_issue_id(self, issue_data: dict, file_path: Path) -> str:
        """Extract issue ID from data or filename.

        Args:
            issue_data: Parsed issue data
            file_path: Path to issue file

        Returns:
            Extracted or derived issue ID
        """
        issue_id = issue_data.get("id")
        if not issue_id:
            stem = file_path.stem
            if stem.startswith("issue-"):
                issue_id = stem[6:]
            else:
                issue_id = stem
            issue_data["id"] = issue_id
        return issue_id

    def _handle_project_id(self, issue_data: dict, issue_id: str) -> str | None:
        """Get project ID for issue, using default if needed.

        Args:
            issue_data: Issue data dict
            issue_id: Issue ID

        Returns:
            Project ID or None if unavailable
        """
        project_id = issue_data.get("project_id")
        if not project_id:
            project_id = self._get_default_project_id()
            if not project_id:
                logger.warning(
                    "no_projects_found_for_issue",
                    issue_id=issue_id,
                    severity="operational",
                )
                return None
        issue_data["project_id"] = project_id
        return project_id

    def _handle_milestone_field(self, issue_data: dict) -> None:
        """Resolve milestone field (could be name or ID).

        Args:
            issue_data: Issue data dict to update
        """
        milestone_id = issue_data.get("milestone_id")
        if not milestone_id and "milestone" in issue_data:
            milestone_name = issue_data["milestone"]
            milestone_id = self._get_milestone_id_by_name(milestone_name)
            issue_data["milestone_id"] = milestone_id

    def _normalize_issue_fields(self, issue_data: dict) -> None:
        """Set defaults and normalize issue fields.

        Args:
            issue_data: Issue data dict to normalize
        """
        issue_data.setdefault("title", "Untitled")
        issue_data.setdefault("status", "open")
        issue_data.setdefault("priority", "medium")
        issue_data.setdefault("issue_type", issue_data.pop("type", "task"))
        issue_data["due_date"] = self._normalize_date(issue_data.get("due_date"))

    def sync_issue_file(self, file_path: Path) -> bool:
        """Sync a single issue file to database."""
        try:
            if not file_path.exists():
                logger.warning(
                    "issue_file_not_found",
                    file_path=str(file_path),
                    severity="operational",
                )
                return False

            # Parse YAML frontmatter
            issue_data = self._parser.parse_yaml_frontmatter(file_path)
            if not issue_data:
                logger.warning(
                    "no_yaml_data_found",
                    file_path=str(file_path),
                    severity="operational",
                )
                return False

            # Extract issue ID
            issue_id = self._extract_issue_id(issue_data, file_path)

            # Handle project ID
            project_id = self._handle_project_id(issue_data, issue_id)
            if not project_id:
                return False

            # Handle milestone field
            self._handle_milestone_field(issue_data)

            # Normalize fields
            self._normalize_issue_fields(issue_data)

            # Extract metadata
            exclude_fields = [
                "id",
                "title",
                "description",
                "status",
                "priority",
                "issue_type",
                "assignee",
                "estimate_hours",
                "due_date",
                "project_id",
                "milestone_id",
            ]
            metadata = self._extract_metadata(issue_data, exclude_fields)

            # Upsert issue
            with self._transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO issues
                    (id, project_id, milestone_id, title, description, status,
                     priority, issue_type, assignee, estimate_hours, due_date, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        issue_data["id"],
                        issue_data["project_id"],
                        issue_data.get("milestone_id"),
                        issue_data["title"],
                        issue_data.get("description"),
                        issue_data["status"],
                        issue_data["priority"],
                        issue_data["issue_type"],
                        issue_data.get("assignee"),
                        issue_data.get("estimate_hours"),
                        issue_data["due_date"],
                        metadata,
                    ),
                )

            # Update sync status
            self._update_sync_status(file_path)
            logger.info(
                "synced_issue_file",
                issue_id=issue_id,
                file_path=str(file_path),
            )
            return True

        except Exception as e:
            logger.error(
                "failed_to_sync_issue_file",
                file_path=str(file_path),
                error=str(e),
                severity="operational",
            )
            return False


class MilestoneSyncCoordinator(EntitySyncCoordinator):
    """Handles syncing milestone files to database."""

    def __init__(self, get_connection, transaction_context):
        """Initialize coordinator with FK validator.

        Args:
            get_connection: Callable that returns a database connection
            transaction_context: Context manager for transactions
        """
        super().__init__(get_connection, transaction_context)
        self._fk_validator = MilestoneFKValidator(get_connection)

    def sync_milestone_file(self, file_path: Path) -> bool:
        """Sync a single milestone file to database.

        Validates foreign key constraints before syncing to prevent
        database corruption from FOREIGN KEY constraint violations.
        """
        try:
            # Validate foreign key constraints first
            try:
                self._fk_validator.validate()
            except ForeignKeyValidationError as fk_error:
                logger.error(
                    "milestone_sync_blocked_by_fk_validation",
                    file_path=str(file_path),
                    entity_type=fk_error.entity_type,
                    error=str(fk_error),
                    severity="operational",
                )
                return False

            if not file_path.exists():
                logger.warning(
                    "milestone_file_not_found",
                    file_path=str(file_path),
                    severity="operational",
                )
                return False

            milestone_data = self._parser.parse_yaml_frontmatter(file_path)
            if not milestone_data:
                logger.warning(
                    "milestone_no_yaml_data_found",
                    file_path=str(file_path),
                    severity="operational",
                )
                return False

            # Extract milestone ID
            milestone_id = milestone_data.get("id", file_path.stem)
            milestone_data["id"] = milestone_id

            # Handle missing project_id
            project_id = milestone_data.get("project_id")
            if not project_id:
                project_id = self._get_default_project_id()
                if not project_id:
                    logger.warning(
                        "no_projects_found_for_milestone",
                        milestone_id=milestone_id,
                        severity="operational",
                    )
                    return False

            # Set defaults and normalize
            title = milestone_data.get("title") or milestone_data.get(
                "name", "Untitled Milestone"
            )
            milestone_data["title"] = title
            milestone_data["status"] = milestone_data.get("status", "open")
            milestone_data["project_id"] = project_id
            milestone_data["progress_percentage"] = milestone_data.get(
                "progress_percentage", 0.0
            )
            milestone_data["due_date"] = self._normalize_date(
                milestone_data.get("due_date")
            )

            # Extract metadata
            exclude_fields = [
                "id",
                "title",
                "description",
                "status",
                "due_date",
                "progress_percentage",
                "project_id",
            ]
            metadata = self._extract_metadata(milestone_data, exclude_fields)

            # Upsert milestone
            with self._transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO milestones
                    (id, project_id, title, description, status, due_date, progress_percentage, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        milestone_data["id"],
                        milestone_data["project_id"],
                        milestone_data["title"],
                        milestone_data.get("description"),
                        milestone_data["status"],
                        milestone_data["due_date"],
                        milestone_data["progress_percentage"],
                        metadata,
                    ),
                )

            # Update sync status
            self._update_sync_status(file_path)
            logger.info(
                "synced_milestone_file",
                milestone_id=milestone_id,
                file_path=str(file_path),
            )
            return True

        except Exception as e:
            logger.error(
                "failed_to_sync_milestone_file",
                file_path=str(file_path),
                error=str(e),
                severity="operational",
            )
            return False


class ProjectSyncCoordinator(EntitySyncCoordinator):
    """Handles syncing project files to database."""

    def sync_project_file(self, file_path: Path) -> bool:
        """Sync a single project file to database."""
        try:
            if not file_path.exists():
                logger.warning(
                    "project_file_not_found",
                    file_path=str(file_path),
                    severity="operational",
                )
                return False

            project_data = self._parser.parse_yaml_frontmatter(file_path)
            if not project_data:
                logger.warning(
                    "project_no_yaml_data_found",
                    file_path=str(file_path),
                    severity="operational",
                )
                return False

            # Extract project ID
            # If not in YAML, extract from filename (format: {uuid}-{name}.md)
            if "id" in project_data:
                project_id = project_data["id"]
            else:
                stem = file_path.stem
                # Check if filename matches UUID pattern (8+ hex chars before hyphen)
                parts = stem.split("-", 1)
                first_part = parts[0]
                # Only treat as UUID if first part is 8+ hex characters
                if len(first_part) >= 8 and all(
                    c in "0123456789abcdefABCDEF" for c in first_part
                ):
                    project_id = first_part  # Use UUID only
                else:
                    project_id = stem  # Use full filename as ID
            project_data["id"] = project_id

            # Set defaults
            name = project_data.get("name") or project_data.get(
                "title", "Untitled Project"
            )
            project_data["name"] = name
            project_data["status"] = project_data.get("status", "active")

            # Extract metadata
            exclude_fields = ["id", "name", "description", "status"]
            metadata = self._extract_metadata(project_data, exclude_fields)

            # Upsert project
            with self._transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO projects
                    (id, name, description, status, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        project_data["id"],
                        project_data["name"],
                        project_data.get("description"),
                        project_data["status"],
                        metadata,
                    ),
                )

            # Update sync status
            self._update_sync_status(file_path)
            logger.info(
                "synced_project_file",
                project_id=project_id,
                file_path=str(file_path),
            )
            return True

        except Exception as e:
            logger.error(
                "failed_to_sync_project_file",
                file_path=str(file_path),
                error=str(e),
                severity="operational",
            )
            return False
