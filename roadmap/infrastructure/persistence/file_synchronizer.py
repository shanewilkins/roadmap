"""File synchronization manager for syncing .roadmap files to database.

This module handles synchronization of markdown files in the .roadmap directory
with the SQLite database, including parsing YAML frontmatter and managing sync state.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ...shared.logging import get_logger

logger = get_logger(__name__)


class FileSynchronizer:
    """Manages synchronization of .roadmap files to the database."""

    def __init__(self, get_connection, transaction_context):
        """Initialize the file synchronizer.

        Args:
            get_connection: Callable that returns a database connection
            transaction_context: Context manager for transactions
        """
        self._get_connection = get_connection
        self._transaction = transaction_context

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate hash for {file_path}", error=str(e))
            return ""

    def _parse_yaml_frontmatter(self, file_path: Path) -> dict[str, Any]:
        """Parse YAML frontmatter from markdown file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check for frontmatter delimiters
            if not content.startswith("---\n"):
                return {}

            # Find the end of frontmatter
            try:
                end_marker = content.index("\n---\n", 4)
                frontmatter = content[4:end_marker]
                return yaml.safe_load(frontmatter) or {}
            except ValueError:
                # No end marker found, treat entire file as YAML
                return yaml.safe_load(content) or {}

        except Exception as e:
            logger.error(f"Failed to parse YAML from {file_path}", error=str(e))
            return {}

    def get_file_sync_status(self, file_path: str) -> dict[str, Any] | None:
        """Get sync status for a file."""
        conn = self._get_connection()
        row = conn.execute(
            """
            SELECT file_path, content_hash, file_size, last_modified, last_synced
            FROM file_sync_state WHERE file_path = ?
        """,
            (file_path,),
        ).fetchone()

        return dict(row) if row else None

    def update_file_sync_status(
        self, file_path: str, content_hash: str, file_size: int, last_modified: datetime
    ):
        """Update sync status for a file."""
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_sync_state
                (file_path, content_hash, file_size, last_modified)
                VALUES (?, ?, ?, ?)
            """,
                (file_path, content_hash, file_size, last_modified),
            )

    def has_file_changed(self, file_path: Path) -> bool:
        """Check if file has changed since last sync."""
        try:
            if not file_path.exists():
                return True

            current_hash = self._calculate_file_hash(file_path)
            sync_status = self.get_file_sync_status(str(file_path))

            if not sync_status:
                return True  # Never synced

            return current_hash != sync_status["content_hash"]

        except Exception as e:
            logger.error(f"Failed to check file changes for {file_path}", error=str(e))
            return True  # Assume changed on error

    def sync_issue_file(self, file_path: Path) -> bool:
        """Sync a single issue file to database."""
        try:
            if not file_path.exists():
                logger.warning(f"Issue file not found: {file_path}")
                return False

            # Parse YAML frontmatter
            issue_data = self._parse_yaml_frontmatter(file_path)
            if not issue_data:
                logger.warning(f"No YAML data found in {file_path}")
                return False

            # Extract issue ID from filename or YAML
            issue_id = issue_data.get("id")
            if not issue_id:
                # Try to extract from filename (e.g., issue-abc123.md -> abc123)
                stem = file_path.stem
                if stem.startswith("issue-"):
                    issue_id = stem[6:]  # Remove 'issue-' prefix
                else:
                    issue_id = stem
                issue_data["id"] = issue_id

            # Handle missing project_id by assigning to first available project
            project_id = issue_data.get("project_id")
            if not project_id:
                project_id = self._get_default_project_id()
                if not project_id:
                    logger.warning(f"No projects found for issue {issue_id}, skipping")
                    return False

            # Handle milestone field (could be name or ID)
            milestone_id = issue_data.get("milestone_id")
            if not milestone_id and "milestone" in issue_data:
                # Convert milestone name to ID
                milestone_name = issue_data["milestone"]
                milestone_id = self._get_milestone_id_by_name(milestone_name)
                issue_data["milestone_id"] = milestone_id

            # Ensure required fields exist
            required_fields = {
                "title": issue_data.get("title", "Untitled"),
                "status": issue_data.get("status", "open"),
                "priority": issue_data.get("priority", "medium"),
                "issue_type": issue_data.get("type", "task"),
                "project_id": project_id,
            }

            for field, default_value in required_fields.items():
                if field not in issue_data:
                    issue_data[field] = default_value

            # Convert dates
            if "due_date" in issue_data and issue_data["due_date"]:
                try:
                    if isinstance(issue_data["due_date"], str):
                        issue_data["due_date"] = datetime.fromisoformat(
                            issue_data["due_date"]
                        ).date()
                except ValueError:
                    issue_data["due_date"] = None

            # Store metadata as JSON
            metadata = {
                k: v
                for k, v in issue_data.items()
                if k
                not in [
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
            }
            issue_data["metadata"] = json.dumps(metadata) if metadata else None

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
                        issue_data.get("due_date"),
                        issue_data["metadata"],
                    ),
                )

            # Update sync status
            file_stat = file_path.stat()
            content_hash = self._calculate_file_hash(file_path)
            self.update_file_sync_status(
                str(file_path),
                content_hash,
                file_stat.st_size,
                datetime.fromtimestamp(file_stat.st_mtime),
            )

            logger.info(f"Synced issue file: {issue_id}", file_path=str(file_path))
            return True

        except Exception as e:
            logger.error(f"Failed to sync issue file {file_path}", error=str(e))
            return False

    def _get_default_project_id(self) -> str | None:
        """Get the first available project ID for orphaned milestones/issues."""
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
            logger.warning(f"Failed to find milestone '{milestone_name}'", error=str(e))
            return None

    def sync_milestone_file(self, file_path: Path) -> bool:
        """Sync a single milestone file to database."""
        try:
            if not file_path.exists():
                logger.warning(f"Milestone file not found: {file_path}")
                return False

            milestone_data = self._parse_yaml_frontmatter(file_path)
            if not milestone_data:
                logger.warning(f"No YAML data found in {file_path}")
                return False

            # Extract milestone ID
            milestone_id = milestone_data.get("id", file_path.stem)
            milestone_data["id"] = milestone_id

            # Handle missing project_id by assigning to first available project
            project_id = milestone_data.get("project_id")
            if not project_id:
                project_id = self._get_default_project_id()
                if not project_id:
                    logger.warning(
                        f"No projects found for milestone {milestone_id}, skipping"
                    )
                    return False

            # Ensure required fields - use 'name' if 'title' is not present
            title = milestone_data.get("title") or milestone_data.get(
                "name", "Untitled Milestone"
            )

            required_fields = {
                "title": title,
                "status": milestone_data.get("status", "open"),
                "project_id": project_id,
                "progress_percentage": milestone_data.get("progress_percentage", 0.0),
            }

            for field, default_value in required_fields.items():
                if field not in milestone_data:
                    milestone_data[field] = default_value

            # Convert dates
            if "due_date" in milestone_data and milestone_data["due_date"]:
                try:
                    if isinstance(milestone_data["due_date"], str):
                        milestone_data["due_date"] = datetime.fromisoformat(
                            milestone_data["due_date"]
                        ).date()
                except ValueError:
                    milestone_data["due_date"] = None

            # Store metadata
            metadata = {
                k: v
                for k, v in milestone_data.items()
                if k
                not in [
                    "id",
                    "title",
                    "description",
                    "status",
                    "due_date",
                    "progress_percentage",
                    "project_id",
                ]
            }
            milestone_data["metadata"] = json.dumps(metadata) if metadata else None

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
                        milestone_data.get("due_date"),
                        milestone_data["progress_percentage"],
                        milestone_data["metadata"],
                    ),
                )

            # Update sync status
            file_stat = file_path.stat()
            content_hash = self._calculate_file_hash(file_path)
            self.update_file_sync_status(
                str(file_path),
                content_hash,
                file_stat.st_size,
                datetime.fromtimestamp(file_stat.st_mtime),
            )

            logger.info(
                f"Synced milestone file: {milestone_id}", file_path=str(file_path)
            )
            return True

        except Exception as e:
            logger.error(f"Failed to sync milestone file {file_path}", error=str(e))
            return False

    def sync_project_file(self, file_path: Path) -> bool:
        """Sync a single project file to database."""
        try:
            if not file_path.exists():
                logger.warning(f"Project file not found: {file_path}")
                return False

            project_data = self._parse_yaml_frontmatter(file_path)
            if not project_data:
                logger.warning(f"No YAML data found in {file_path}")
                return False

            # Extract project ID
            project_id = project_data.get("id", file_path.stem)
            project_data["id"] = project_id

            # Ensure required fields
            required_fields = {
                "name": project_data.get(
                    "name", project_data.get("title", "Untitled Project")
                ),
                "status": project_data.get("status", "active"),
            }

            for field, default_value in required_fields.items():
                if field not in project_data:
                    project_data[field] = default_value

            # Store metadata
            metadata = {
                k: v
                for k, v in project_data.items()
                if k not in ["id", "name", "description", "status"]
            }
            project_data["metadata"] = json.dumps(metadata) if metadata else None

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
                        project_data["metadata"],
                    ),
                )

            # Update sync status
            file_stat = file_path.stat()
            content_hash = self._calculate_file_hash(file_path)
            self.update_file_sync_status(
                str(file_path),
                content_hash,
                file_stat.st_size,
                datetime.fromtimestamp(file_stat.st_mtime),
            )

            logger.info(f"Synced project file: {project_id}", file_path=str(file_path))
            return True

        except Exception as e:
            logger.error(f"Failed to sync project file {file_path}", error=str(e))
            return False

    def sync_directory_incremental(self, roadmap_dir: Path) -> dict[str, Any]:
        """Incrementally sync .roadmap directory to database."""
        stats = {
            "files_checked": 0,
            "files_changed": 0,
            "files_synced": 0,
            "files_failed": 0,
            "sync_time": datetime.now(),
        }

        try:
            if not roadmap_dir.exists():
                logger.warning(f"Roadmap directory not found: {roadmap_dir}")
                return stats

            # Process in dependency order: projects first, then milestones, then issues
            for directory, pattern in [
                ("projects", "projects/**/*.md"),
                ("milestones", "milestones/**/*.md"),
                ("issues", "issues/**/*.md"),
            ]:
                dir_path = roadmap_dir / directory
                if dir_path.exists():
                    for file_path in roadmap_dir.glob(pattern):
                        stats["files_checked"] += 1
                        if self.has_file_changed(file_path):
                            stats["files_changed"] += 1

                            if "issues/" in str(file_path):
                                success = self.sync_issue_file(file_path)
                            elif "milestones/" in str(file_path):
                                success = self.sync_milestone_file(file_path)
                            elif "projects/" in str(file_path):
                                success = self.sync_project_file(file_path)
                            else:
                                continue

                            if success:
                                stats["files_synced"] += 1
                            else:
                                stats["files_failed"] += 1

            # Update last sync time
            conn = self._get_connection()
            conn.execute(
                "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)",
                ("last_incremental_sync", str(stats["sync_time"])),
            )

            logger.info(
                "Incremental sync completed",
                **{k: v for k, v in stats.items() if k != "sync_time"},
            )
            return stats

        except Exception as e:
            logger.error("Incremental sync failed", error=str(e))
            stats["files_failed"] += 1
            return stats

    def full_rebuild_from_git(self, roadmap_dir: Path) -> dict[str, Any]:
        """Full rebuild of database from git files."""
        stats = {
            "files_processed": 0,
            "files_changed": 0,  # All files are "changed" in a full rebuild
            "files_synced": 0,
            "files_failed": 0,
            "rebuild_time": datetime.now(),
        }

        try:
            if not roadmap_dir.exists():
                logger.warning(f"Roadmap directory not found: {roadmap_dir}")
                return stats

            # Clear existing sync state
            with self._transaction() as conn:
                conn.execute("DELETE FROM file_sync_state")
                conn.execute("DELETE FROM issues")
                conn.execute("DELETE FROM milestones")
                conn.execute("DELETE FROM projects")

            logger.info("Starting full rebuild from git files")

            # Rebuild from all files in dependency order (projects first, then milestones, then issues)
            for pattern in ["projects/**/*.md", "milestones/**/*.md", "issues/**/*.md"]:
                for file_path in roadmap_dir.glob(pattern):
                    stats["files_processed"] += 1
                    stats["files_changed"] += (
                        1  # All files are "changed" in full rebuild
                    )

                    if "issues/" in str(file_path):
                        success = self.sync_issue_file(file_path)
                    elif "milestones/" in str(file_path):
                        success = self.sync_milestone_file(file_path)
                    elif "projects/" in str(file_path):
                        success = self.sync_project_file(file_path)
                    else:
                        continue

                    if success:
                        stats["files_synced"] += 1
                    else:
                        stats["files_failed"] += 1

            # Update sync state
            conn = self._get_connection()
            conn.execute(
                "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)",
                ("last_full_rebuild", str(stats["rebuild_time"])),
            )
            conn.execute(
                "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)",
                ("rebuild_reason", "manual_full_rebuild"),
            )

            logger.info(
                "Full rebuild completed",
                **{k: v for k, v in stats.items() if k != "rebuild_time"},
            )
            return stats

        except Exception as e:
            logger.error("Full rebuild failed", error=str(e))
            return stats

    def should_do_full_rebuild(self, roadmap_dir: Path, threshold: int = 50) -> bool:
        """Determine if full rebuild is needed vs incremental sync."""
        try:
            # Count total files
            total_files = 0
            for pattern in ["issues/**/*.md", "milestones/**/*.md", "projects/**/*.md"]:
                total_files += len(list(roadmap_dir.glob(pattern)))

            # Count changed files
            changed_files = 0
            for pattern in [
                "issues/**/*.md",
                "milestones/**/*.md",
                "projects/**/*.md",
            ]:
                for file_path in roadmap_dir.glob(pattern):
                    if self.has_file_changed(file_path):
                        changed_files += 1

            # Check for missing sync state
            conn = self._get_connection()
            last_sync = conn.execute(
                "SELECT value FROM sync_state WHERE key = ?",
                ("last_incremental_sync",),
            ).fetchone()
            if not last_sync:
                logger.info("No previous sync found, triggering full rebuild")
                return True

            # Threshold-based decision
            if total_files > 0 and (changed_files / total_files) >= threshold / 100:
                logger.info(
                    f"Many files changed ({changed_files}/{total_files}), triggering full rebuild"
                )
                return True

            return False

        except Exception as e:
            logger.error("Failed to determine rebuild strategy", error=str(e))
            return True  # Default to full rebuild on error
