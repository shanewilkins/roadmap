"""Specialized synchronizers for different entity types."""

import json
from pathlib import Path
from typing import Any

from roadmap.adapters.persistence.file_parser import FileParser
from roadmap.common.datetime_parser import UnifiedDateTimeParser
from roadmap.common.logging import get_logger

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
            logger.error("Failed to get default project ID", error=str(e))
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
        return json.dumps(metadata) if metadata else None

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

    def sync_milestone_file(self, file_path: Path) -> bool:
        """Sync a single milestone file to database."""
        try:
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
                        f"No projects found for milestone {milestone_id}, skipping"
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
                f"Synced milestone file: {milestone_id}", file_path=str(file_path)
            )
            return True

        except Exception as e:
            logger.error(f"Failed to sync milestone file {file_path}", error=str(e))
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
            project_id = project_data.get("id", file_path.stem)
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
            logger.error(f"Failed to sync project file {file_path}", error=str(e))
            return False
