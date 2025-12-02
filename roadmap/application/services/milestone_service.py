"""Milestone service - handles all milestone-related operations.

The MilestoneService manages:
- Milestone creation with metadata
- Milestone listing and sorting
- Getting specific milestones by name
- Updating milestone properties
- Deleting milestones (with issue cleanup)
- Progress calculation
- Status tracking

Extracted from core.py to separate business logic.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from roadmap.domain.issue import Status
from roadmap.domain.milestone import Milestone, MilestoneStatus
from roadmap.infrastructure.persistence.parser import IssueParser, MilestoneParser
from roadmap.infrastructure.storage import StateManager
from roadmap.shared.timezone_utils import now_utc


class MilestoneService:
    """Service for managing milestones."""

    def __init__(self, db: StateManager, milestones_dir: Path, issues_dir: Path):
        """Initialize milestone service.

        Args:
            db: State manager for database operations
            milestones_dir: Path to milestones directory
            issues_dir: Path to issues directory (for cleanup)
        """
        self.db = db
        self.milestones_dir = milestones_dir
        self.issues_dir = issues_dir

    def create_milestone(
        self,
        name: str,
        description: str = "",
        due_date: datetime | None = None,
    ) -> Milestone:
        """Create a new milestone.

        Args:
            name: Milestone name/title
            description: Milestone description
            due_date: Target completion date

        Returns:
            Newly created Milestone object
        """
        import json
        import uuid

        milestone = Milestone(
            name=name,
            description=description,
            due_date=due_date,
            content=f"# {name}\n\n## Description\n\n{description}\n\n## Goals\n\n- [ ] Goal 1\n- [ ] Goal 2\n- [ ] Goal 3",
        )

        milestone_path = self.milestones_dir / milestone.filename
        MilestoneParser.save_milestone_file(milestone, milestone_path)

        # Persist to database (non-blocking - file system is primary source of truth)
        try:
            milestone_id = str(uuid.uuid4())[:8]
            self.db.create_milestone(
                {
                    "id": milestone_id,
                    "project_id": None,  # Milestones are not project-scoped in current design
                    "title": name,
                    "description": description,
                    "status": "open",
                    "due_date": due_date.isoformat() if due_date else None,
                    "metadata": json.dumps({"filename": milestone.filename}),
                }
            )
        except Exception:
            # Silently continue if DB insert fails - file-based system is primary
            pass

        return milestone

    def list_milestones(self, status: MilestoneStatus | None = None) -> list[Milestone]:
        """List all milestones with optional status filter.

        Args:
            status: Optional status filter

        Returns:
            List of Milestone objects sorted by due date then name
        """
        milestones = []
        for milestone_file in self.milestones_dir.rglob("*.md"):
            try:
                milestone = MilestoneParser.parse_milestone_file(milestone_file)
                if status is None or milestone.status == status:
                    milestones.append(milestone)
            except Exception:
                continue

        # Sort by due date (earliest first), then by name
        def get_sortable_date(milestone):
            if milestone.due_date is None:
                return datetime.max
            # Convert timezone-aware to naive for comparison
            if milestone.due_date.tzinfo is not None:
                return milestone.due_date.replace(tzinfo=None)
            return milestone.due_date

        milestones.sort(key=lambda x: (get_sortable_date(x), x.name))
        return milestones

    def get_milestone(self, name: str) -> Milestone | None:
        """Get a specific milestone by name.

        Args:
            name: Milestone name

        Returns:
            Milestone object if found, None otherwise
        """
        for milestone_file in self.milestones_dir.rglob("*.md"):
            try:
                milestone = MilestoneParser.parse_milestone_file(milestone_file)
                if milestone.name == name:
                    return milestone
            except Exception:
                continue
        return None

    def update_milestone(
        self,
        name: str,
        description: str | None = None,
        due_date: datetime | None = None,
        clear_due_date: bool = False,
        status: str | None = None,
    ) -> Milestone | None:
        """Update a milestone's properties.

        Args:
            name: Milestone name
            description: New description (None to keep current)
            due_date: New due date (None to keep current)
            clear_due_date: If True, remove the due date
            status: New status

        Returns:
            Updated Milestone object if found, None otherwise
        """
        milestone = self.get_milestone(name)
        if not milestone:
            return None

        # Update fields if provided
        if description is not None:
            milestone.description = description

        if clear_due_date:
            milestone.due_date = None
        elif due_date is not None:
            milestone.due_date = due_date

        if status is not None:
            milestone.status = MilestoneStatus(status)

        milestone.updated = now_utc()

        # Save the updated milestone
        for milestone_file in self.milestones_dir.rglob("*.md"):
            try:
                test_milestone = MilestoneParser.parse_milestone_file(milestone_file)
                if test_milestone.name == name:
                    MilestoneParser.save_milestone_file(milestone, milestone_file)
                    return milestone
            except Exception:
                continue
        return None

    def delete_milestone(self, name: str) -> bool:
        """Delete a milestone and unassign all issues from it.

        Args:
            name: Milestone name

        Returns:
            True if deleted, False if not found
        """
        # Check if milestone exists
        milestone = self.get_milestone(name)
        if not milestone:
            return False

        # Unassign all issues from this milestone
        for issue_file in self.issues_dir.rglob("*.md"):
            try:
                issue = IssueParser.parse_issue_file(issue_file)
                if issue.milestone == name:
                    issue.milestone = None
                    issue.updated = now_utc()
                    IssueParser.save_issue_file(issue, issue_file)
            except Exception:
                continue

        # Delete the milestone file
        for milestone_file in self.milestones_dir.rglob("*.md"):
            try:
                test_milestone = MilestoneParser.parse_milestone_file(milestone_file)
                if test_milestone.name == name:
                    milestone_file.unlink()
                    return True
            except Exception:
                continue
        return False

    def get_milestone_progress(self, milestone_name: str) -> dict[str, Any]:
        """Get progress statistics for a milestone.

        Args:
            milestone_name: Milestone name

        Returns:
            Dict with total, completed, progress percentage, and status breakdown
        """
        issues = []
        for issue_file in self.issues_dir.rglob("*.md"):
            try:
                issue = IssueParser.parse_issue_file(issue_file)
                if issue.milestone == milestone_name:
                    issues.append(issue)
            except Exception:
                continue

        if not issues:
            return {"total": 0, "completed": 0, "progress": 0.0, "by_status": {}}

        total = len(issues)
        completed = len([i for i in issues if i.status == Status.CLOSED])
        progress = (completed / total) * 100 if total > 0 else 0.0

        by_status = {}
        for status in Status:
            by_status[status.value] = len([i for i in issues if i.status == status])

        return {
            "total": total,
            "completed": completed,
            "progress": progress,
            "by_status": by_status,
        }

    def close_milestone(self, name: str) -> Milestone | None:
        """Close/mark milestone as closed.

        Args:
            name: Milestone name

        Returns:
            Closed Milestone object if found, None otherwise
        """
        return self.update_milestone(name, status=MilestoneStatus.CLOSED.value)
