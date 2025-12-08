"""Database query service for aggregations and complex queries."""

import hashlib
import json
from typing import TYPE_CHECKING, Any

from roadmap.common.logging import get_logger

if TYPE_CHECKING:
    from .state_manager import StateManager

logger = get_logger(__name__)


class QueryService:
    """Service for executing complex database queries and aggregations."""

    def __init__(self, state_manager: "StateManager"):
        """Initialize with reference to state manager.

        Args:
            state_manager: StateManager instance for database access
        """
        self.state_manager = state_manager

    def has_file_changes(self) -> bool:
        """Check if .roadmap/ files have changes since last sync."""
        try:
            # Get roadmap directory from database path
            roadmap_dir = self.state_manager.db_path.parent

            # Check for Markdown files with YAML frontmatter in relevant directories
            md_files = []
            for subdir in ["issues", "milestones", "projects"]:
                subdir_path = roadmap_dir / subdir
                if subdir_path.exists():
                    md_files.extend(subdir_path.rglob("*.md"))

            if not md_files:
                return False

            # Check each file against stored hash
            with self.state_manager.transaction() as conn:
                for file_path in md_files:
                    if not file_path.exists():
                        continue

                    # Calculate current hash
                    current_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

                    # Get stored hash
                    result = conn.execute(
                        "SELECT content_hash FROM file_sync_state WHERE file_path = ?",
                        (str(file_path.relative_to(roadmap_dir)),),
                    ).fetchone()

                    if not result or result[0] != current_hash:
                        # File is new or changed
                        return True

            return False

        except Exception as e:
            logger.warning("Error checking file changes", error=str(e))
            # If we can't check, assume changes exist to be safe
            return True

    def get_all_issues(self) -> list[dict[str, Any]]:
        """Get all issues from database."""
        try:
            with self.state_manager.transaction() as conn:
                results = conn.execute("""
                    SELECT i.id, i.title, i.status, i.priority, i.issue_type,
                           i.assignee, i.estimate_hours, i.due_date,
                           i.project_id, i.milestone_id, i.metadata,
                           m.title as milestone_name, p.name as project_name
                    FROM issues i
                    LEFT JOIN milestones m ON i.milestone_id = m.id
                    LEFT JOIN projects p ON i.project_id = p.id
                    ORDER BY i.title
                """).fetchall()

                issues = []
                for row in results:
                    issue = {
                        "id": row[0],
                        "title": row[1],
                        "status": row[2],
                        "priority": row[3],
                        "type": row[4],
                        "assignee": row[5],
                        "estimate_hours": row[6],
                        "due_date": row[7],
                        "project_id": row[8],
                        "milestone_id": row[9],
                        "milestone_name": row[11],
                        "project_name": row[12],
                    }

                    # Parse metadata
                    if row[10]:
                        try:
                            metadata = json.loads(row[10])
                            issue.update(metadata)
                        except json.JSONDecodeError:
                            pass

                    issues.append(issue)

                return issues

        except Exception as e:
            logger.error("Failed to get issues", error=str(e))
            return []

    def get_all_milestones(self) -> list[dict[str, Any]]:
        """Get all milestones from database."""
        try:
            with self.state_manager.transaction() as conn:
                results = conn.execute("""
                    SELECT m.id, m.title, m.description, m.status, m.due_date,
                           m.progress_percentage, m.project_id, m.metadata,
                           p.name as project_name
                    FROM milestones m
                    LEFT JOIN projects p ON m.project_id = p.id
                    ORDER BY m.title
                """).fetchall()

                milestones = []
                for row in results:
                    milestone = {
                        "id": row[0],
                        "name": row[1],  # Use 'name' for compatibility
                        "title": row[1],
                        "description": row[2],
                        "status": row[3],
                        "due_date": row[4],
                        "progress_percentage": row[5],
                        "project_id": row[6],
                        "project_name": row[8],
                    }

                    # Parse metadata
                    if row[7]:
                        try:
                            metadata = json.loads(row[7])
                            milestone.update(metadata)
                        except json.JSONDecodeError:
                            pass

                    milestones.append(milestone)

                return milestones

        except Exception as e:
            logger.error("Failed to get milestones", error=str(e))
            return []

    def get_milestone_progress(self, milestone_name: str) -> dict[str, int]:
        """Get progress stats for a milestone."""
        try:
            with self.state_manager.transaction() as conn:
                # Get milestone ID first
                milestone_result = conn.execute(
                    "SELECT id FROM milestones WHERE title = ?", (milestone_name,)
                ).fetchone()

                if not milestone_result:
                    return {"total": 0, "completed": 0}

                milestone_id = milestone_result[0]

                # Count total and done issues for this milestone
                total_result = conn.execute(
                    "SELECT COUNT(*) FROM issues WHERE milestone_id = ?",
                    (milestone_id,),
                ).fetchone()

                completed_result = conn.execute(
                    "SELECT COUNT(*) FROM issues WHERE milestone_id = ? AND status = 'closed'",
                    (milestone_id,),
                ).fetchone()

                return {
                    "total": total_result[0] if total_result else 0,
                    "completed": completed_result[0] if completed_result else 0,
                }

        except Exception as e:
            logger.error(
                f"Failed to get milestone progress for {milestone_name}", error=str(e)
            )
            return {"total": 0, "completed": 0}

    def get_issues_by_status(self) -> dict[str, int]:
        """Get issue counts by status."""
        try:
            with self.state_manager.transaction() as conn:
                results = conn.execute("""
                    SELECT status, COUNT(*)
                    FROM issues
                    GROUP BY status
                    ORDER BY status
                """).fetchall()

                return {row[0]: row[1] for row in results}

        except Exception as e:
            logger.error("Failed to get issues by status", error=str(e))
            return {}
