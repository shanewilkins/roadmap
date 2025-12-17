"""YAML-based repository implementations.

This module provides concrete implementations of repository protocols
using YAML file storage, maintaining backward compatibility with existing
file-based storage while decoupling services from implementation details.
"""

from pathlib import Path

from roadmap.adapters.persistence.parser import (
    IssueParser,
    MilestoneParser,
    ProjectParser,
)
from roadmap.adapters.persistence.storage import StateManager
from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone
from roadmap.core.domain.project import Project
from roadmap.core.repositories import (
    IssueRepository,
    MilestoneRepository,
    ProjectRepository,
)
from roadmap.infrastructure.file_enumeration import FileEnumerationService


class YAMLIssueRepository(IssueRepository):
    """Issue repository using YAML file storage."""

    def __init__(self, db: StateManager, issues_dir: Path):
        """Initialize issue repository.

        Args:
            db: State manager for metadata operations
            issues_dir: Path to issues directory containing issue markdown files
        """
        self.db = db
        self.issues_dir = issues_dir

    def get(self, issue_id: str) -> Issue | None:
        """Get a specific issue by ID.

        Args:
            issue_id: Issue identifier

        Returns:
            Issue object if found, None otherwise
        """

        def id_matcher(issue: Issue) -> bool:
            return issue.id.startswith(issue_id)

        issues = FileEnumerationService.enumerate_with_filter(
            self.issues_dir,
            IssueParser.parse_issue_file,
            id_matcher,
        )
        return issues[0] if issues else None

    def list(
        self, milestone: str | None = None, status: str | None = None
    ) -> list[Issue]:
        """List issues with optional filtering.

        Args:
            milestone: Optional milestone filter
            status: Optional status filter

        Returns:
            List of Issue objects matching filters
        """
        issues = FileEnumerationService.enumerate_and_parse(
            self.issues_dir,
            IssueParser.parse_issue_file,
        )

        if milestone:
            issues = [i for i in issues if i.milestone == milestone]
        if status:
            issues = [i for i in issues if i.status.value == status]

        return issues

    def save(self, issue: Issue) -> None:
        """Save/create an issue.

        Args:
            issue: Issue object to save
        """
        issue_path = self.issues_dir / issue.filename
        IssueParser.save_issue_file(issue, issue_path)

    def update(self, issue_id: str, updates: dict) -> Issue | None:
        """Update specific fields of an issue.

        Args:
            issue_id: Issue identifier
            updates: Dictionary of field updates

        Returns:
            Updated Issue object if found, None otherwise
        """
        issue = self.get(issue_id)
        if not issue:
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(issue, key):
                setattr(issue, key, value)

        # Save back
        self.save(issue)
        return issue

    def delete(self, issue_id: str) -> bool:
        """Delete an issue.

        Args:
            issue_id: Issue identifier

        Returns:
            True if deleted, False if not found
        """
        issue = self.get(issue_id)
        if not issue:
            return False

        issue_path = self.issues_dir / issue.filename
        if issue_path.exists():
            try:
                issue_path.unlink()
            except (OSError, PermissionError):
                return False

        return True


class YAMLMilestoneRepository(MilestoneRepository):
    """Milestone repository using YAML file storage."""

    def __init__(self, db: StateManager, milestones_dir: Path):
        """Initialize milestone repository.

        Args:
            db: State manager for metadata operations
            milestones_dir: Path to milestones directory
        """
        self.db = db
        self.milestones_dir = milestones_dir

    def get(self, milestone_id: str) -> Milestone | None:
        """Get a specific milestone by ID or name.

        Args:
            milestone_id: Milestone identifier or name

        Returns:
            Milestone object if found, None otherwise
        """

        def id_matcher(milestone: Milestone) -> bool:
            return milestone.name.lower().startswith(milestone_id.lower())

        milestones = FileEnumerationService.enumerate_with_filter(
            self.milestones_dir,
            MilestoneParser.parse_milestone_file,
            id_matcher,
        )
        return milestones[0] if milestones else None

    def list(self) -> list[Milestone]:
        """List all milestones.

        Returns:
            List of all Milestone objects
        """
        return FileEnumerationService.enumerate_and_parse(
            self.milestones_dir,
            MilestoneParser.parse_milestone_file,
        )

    def save(self, milestone: Milestone) -> None:
        """Save/create a milestone.

        Args:
            milestone: Milestone object to save
        """
        milestone_path = self.milestones_dir / milestone.filename
        MilestoneParser.save_milestone_file(milestone, milestone_path)

        # Persist metadata to database (non-blocking)
        try:
            self.db.create_milestone(
                {
                    "title": milestone.name,
                    "description": milestone.description,
                    "status": milestone.status.value,
                }
            )
        except Exception:
            pass

    def update(self, milestone_id: str, updates: dict) -> Milestone | None:
        """Update specific fields of a milestone.

        Args:
            milestone_id: Milestone identifier
            updates: Dictionary of field updates

        Returns:
            Updated Milestone object if found, None otherwise
        """
        milestone = self.get(milestone_id)
        if not milestone:
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(milestone, key):
                setattr(milestone, key, value)

        # Save back
        self.save(milestone)
        return milestone

    def delete(self, milestone_id: str) -> bool:
        """Delete a milestone.

        Args:
            milestone_id: Milestone identifier

        Returns:
            True if deleted, False if not found
        """
        milestone = self.get(milestone_id)
        if not milestone:
            return False

        milestone_path = self.milestones_dir / milestone.filename
        if milestone_path.exists():
            try:
                milestone_path.unlink()
            except (OSError, PermissionError):
                return False

        return True


class YAMLProjectRepository(ProjectRepository):
    """Project repository using YAML file storage."""

    def __init__(self, db: StateManager, projects_dir: Path):
        """Initialize project repository.

        Args:
            db: State manager for metadata operations
            projects_dir: Path to projects directory
        """
        self.db = db
        self.projects_dir = projects_dir

    def get(self, project_id: str) -> Project | None:
        """Get a specific project by ID.

        Args:
            project_id: Project identifier

        Returns:
            Project object if found, None otherwise
        """

        def id_matcher(project: Project) -> bool:
            return project.id.startswith(project_id)

        projects = FileEnumerationService.enumerate_with_filter(
            self.projects_dir,
            ProjectParser.parse_project_file,
            id_matcher,
        )
        return projects[0] if projects else None

    def list(self) -> list[Project]:
        """List all projects.

        Returns:
            List of all Project objects
        """
        projects = FileEnumerationService.enumerate_and_parse(
            self.projects_dir,
            ProjectParser.parse_project_file,
        )
        return sorted(projects, key=lambda x: x.created)

    def save(self, project: Project) -> None:
        """Save/create a project.

        Args:
            project: Project object to save
        """
        project_path = self.projects_dir / project.filename
        ProjectParser.save_project_file(project, project_path)

        # Persist metadata to database (non-blocking)
        try:
            self.db.create_project(
                {
                    "title": project.name,
                    "description": project.description,
                    "status": project.status.value,
                }
            )
        except Exception:
            pass

    def update(self, project_id: str, updates: dict) -> Project | None:
        """Update specific fields of a project.

        Args:
            project_id: Project identifier
            updates: Dictionary of field updates

        Returns:
            Updated Project object if found, None otherwise
        """
        project = self.get(project_id)
        if not project:
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(project, key):
                setattr(project, key, value)

        # Save back
        self.save(project)
        return project

    def delete(self, project_id: str) -> bool:
        """Delete a project.

        Args:
            project_id: Project identifier

        Returns:
            True if deleted, False if not found
        """
        project = self.get(project_id)
        if not project:
            return False

        project_path = self.projects_dir / project.filename
        if project_path.exists():
            try:
                project_path.unlink()
            except (OSError, PermissionError):
                return False

        return True
