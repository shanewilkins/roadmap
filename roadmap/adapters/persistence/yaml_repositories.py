"""YAML-based repository implementations.

This module provides concrete implementations of repository protocols
using YAML file storage, maintaining backward compatibility with existing
file-based storage while decoupling services from implementation details.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from roadmap.adapters.persistence.parser import (
    IssueParser,
    MilestoneParser,
    ProjectParser,
)
from roadmap.adapters.persistence.storage import StateManager
from roadmap.common.logging import get_logger
from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone
from roadmap.core.domain.project import Project
from roadmap.core.repositories import (
    IssueRepository,
    MilestoneRepository,
    ProjectRepository,
)
from roadmap.infrastructure.validation.file_enumeration import FileEnumerationService

logger = get_logger(__name__)


class YAMLIssueRepository(IssueRepository):
    """Issue repository using YAML file storage.

    This repository implements a file-based storage system with the following
    organizational contract:

    **File Organization by Milestone:**
    - Issues with no milestone → `.roadmap/issues/backlog/`
    - Issues with milestone "M1" → `.roadmap/issues/M1/`
    - Archived issues with no milestone → `.roadmap/archive/issues/backlog/`
    - Archived issues with milestone "M1" → `.roadmap/archive/issues/M1/`

    **Duplicate Prevention:**
    - save() method cleans up stale copies in other directories before writing
    - update() with milestone change uses atomic file moves
    - Only one file per issue exists at any time

    **Key Invariants:**
    - Each issue has exactly one file in the filesystem
    - File location matches issue.milestone value
    - issue.file_path always points to actual file location
    - No orphaned copies left in subdirectories after moves

    **Error Handling:**
    - If cleanup fails, logs warning but continues (fail-open)
    - If save fails, raises exception (fail-safe)
    - Atomic rename ensures consistency
    """

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
        """List issues with optional filtering (active issues only).

        Args:
            milestone: Optional milestone filter
            status: Optional status filter

        Returns:
            List of active Issue objects matching filters (not including archived)
        """
        # Get issues from active directory only
        issues = FileEnumerationService.enumerate_and_parse(
            self.issues_dir,
            IssueParser.parse_issue_file,
        )

        if milestone:
            issues = [i for i in issues if i.milestone == milestone]
        if status:
            issues = [i for i in issues if i.status.value == status]

        return issues

    def list_all_including_archived(
        self, milestone: str | None = None, status: str | None = None
    ) -> list[Issue]:
        """List all issues including archived (for sync operations).

        Args:
            milestone: Optional milestone filter
            status: Optional status filter

        Returns:
            List of all Issue objects matching filters (from both active and archived)
        """
        # Get issues from active directory
        issues = FileEnumerationService.enumerate_and_parse(
            self.issues_dir,
            IssueParser.parse_issue_file,
        )

        # Also get issues from archive directory if it exists
        archive_dir = self.issues_dir.parent / "archive" / "issues"
        if archive_dir.exists():
            archived_issues = FileEnumerationService.enumerate_and_parse(
                archive_dir,
                IssueParser.parse_issue_file,
            )
            issues.extend(archived_issues)

        if milestone:
            issues = [i for i in issues if i.milestone == milestone]
        if status:
            issues = [i for i in issues if i.status.value == status]

        return issues

    def save(self, issue: Issue) -> None:
        """Save/create an issue.

        Ensures single file location by cleaning up any stale copies in other directories.
        This prevents duplicate files when issues are moved between milestones or when
        the issue filename changes (e.g., due to title updates).

        Args:
            issue: Issue object to save
        """
        # Determine target directory based on milestone
        if issue.milestone and issue.milestone != "backlog":
            # Save to milestone-specific directory
            target_dir = self.issues_dir / issue.milestone
        else:
            # Save to backlog directory for unassigned issues
            target_dir = self.issues_dir / "backlog"

        # Create directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)

        # Check if file exists in other locations and remove it
        # This handles issue moves between milestones
        issue_path_target = target_dir / issue.filename
        stale_files_removed = 0

        # Search for any existing files with this issue ID but different filenames
        # This handles the case where the title (and thus filename) has changed
        issue_id_prefix = issue.id
        for subdir in self.issues_dir.glob("*"):
            if subdir.is_dir():
                # Look for files matching this issue ID
                for existing_file in subdir.glob(f"{issue_id_prefix}-*.md"):
                    # Skip the target file we're about to create
                    if existing_file != issue_path_target:
                        try:
                            existing_file.unlink()
                            stale_files_removed += 1
                            logger.debug(
                                "removed_stale_issue_file_by_id",
                                issue_id=issue.id,
                                old_filename=existing_file.name,
                                removed_path=str(existing_file),
                                target_path=str(issue_path_target),
                            )
                        except (OSError, PermissionError) as e:
                            logger.warning(
                                "failed_to_remove_stale_issue_file_by_id",
                                issue_id=issue.id,
                                old_filename=existing_file.name,
                                path=str(existing_file),
                                error=str(e),
                            )

        # Also check in root for backward compatibility
        root_files = list(self.issues_dir.glob(f"{issue_id_prefix}-*.md"))
        for root_path in root_files:
            if root_path != issue_path_target:
                try:
                    root_path.unlink()
                    stale_files_removed += 1
                    logger.debug(
                        "removed_stale_issue_file_from_root",
                        issue_id=issue.id,
                        old_filename=root_path.name,
                        removed_path=str(root_path),
                        target_path=str(issue_path_target),
                    )
                except (OSError, PermissionError) as e:
                    logger.warning(
                        "failed_to_remove_stale_issue_file_from_root",
                        issue_id=issue.id,
                        old_filename=root_path.name,
                        path=str(root_path),
                        error=str(e),
                    )

        # Save file to proper location
        IssueParser.save_issue_file(issue, issue_path_target)
        logger.debug(
            "issue_saved",
            issue_id=issue.id,
            filename=issue.filename,
            milestone=issue.milestone,
            target_directory=str(target_dir),
            stale_files_removed=stale_files_removed,
        )

        # Set the file_path on the issue object so it reflects the saved location
        issue.file_path = str(issue_path_target)

    def update(self, issue_id: str, updates: dict) -> Issue | None:
        """Update specific fields of an issue.

        When milestone changes, moves file to appropriate directory and removes
        any stale copies from other locations. For non-milestone updates, saves
        to current file location without moving.

        Args:
            issue_id: Issue identifier
            updates: Dictionary of field updates (may include milestone to trigger move)

        Returns:
            Updated Issue object if found, None otherwise
        """
        issue = self.get(issue_id)
        if not issue:
            logger.debug("issue_not_found_for_update", issue_id=issue_id)
            return None

        # Track old state before modification
        old_milestone = issue.milestone
        old_filename = issue.filename

        logger.debug(
            "updating_issue",
            issue_id=issue_id,
            old_milestone=old_milestone,
            update_fields=list(updates.keys()),
        )

        # Apply updates to issue object
        for key, value in updates.items():
            if hasattr(issue, key):
                setattr(issue, key, value)

        # Handle file system changes based on what was updated
        if "milestone" in updates and old_milestone != issue.milestone:
            self._handle_milestone_change(issue, old_milestone)
        elif old_filename != issue.filename:
            self._handle_filename_change(issue, old_filename)

        # Save and return updated issue
        self.save(issue)
        return issue

    def _handle_milestone_change(self, issue: Issue, old_milestone: str | None) -> None:
        """Handle file move when issue's milestone changes.

        Args:
            issue: Updated issue object
            old_milestone: Previous milestone value
        """
        old_path = self._get_issue_path(old_milestone, issue.filename)
        new_path = self._get_issue_path(issue.milestone, issue.filename)

        # Create destination directory if needed
        new_path.parent.mkdir(parents=True, exist_ok=True)

        # Move file to new location
        if old_path.exists():
            try:
                shutil.move(str(old_path), str(new_path))
            except (OSError, PermissionError):
                # If move fails, save to new location directly
                IssueParser.save_issue_file(issue, new_path)
        else:
            # File doesn't exist at old location, save to new location
            IssueParser.save_issue_file(issue, new_path)

        # Clean up stale copies from other directories
        self._cleanup_stale_files(issue.filename, new_path.parent)

        # Update the issue's file path
        issue.file_path = str(new_path)

        logger.info(
            "issue_milestone_updated",
            issue_id=issue.id,
            old_milestone=old_milestone,
            new_milestone=issue.milestone,
            new_path=str(new_path),
        )

    def _handle_filename_change(self, issue: Issue, old_filename: str) -> None:
        """Handle file removal when issue's filename changes.

        Args:
            issue: Updated issue object
            old_filename: Previous filename
        """
        # Get current directory for issue
        target_dir = self._get_milestone_dir(issue.milestone)

        # Remove old file from target directory
        old_path = target_dir / old_filename
        if old_path.exists():
            try:
                old_path.unlink()
                logger.debug(
                    "removed_old_filename_after_update",
                    issue_id=issue.id,
                    old_filename=old_filename,
                )
            except (OSError, PermissionError) as e:
                logger.warning(
                    "failed_to_remove_old_filename",
                    issue_id=issue.id,
                    error=str(e),
                )

        # Also check for stale copies in other directories
        self._cleanup_stale_files(old_filename, target_dir)

    def _get_issue_path(self, milestone: str | None, filename: str) -> Path:
        """Get the full path for an issue file.

        Args:
            milestone: Issue milestone (None or "backlog" means backlog dir)
            filename: Issue filename

        Returns:
            Full path to issue file
        """
        return self._get_milestone_dir(milestone) / filename

    def _get_milestone_dir(self, milestone: str | None) -> Path:
        """Get directory for a milestone.

        Args:
            milestone: Milestone name (None or "backlog" means backlog)

        Returns:
            Directory path
        """
        if milestone and milestone != "backlog":
            return self.issues_dir / milestone
        return self.issues_dir / "backlog"

    def _cleanup_stale_files(self, filename: str, exclude_dir: Path) -> None:
        """Remove stale copies of a file from other directories.

        Args:
            filename: Filename to search for
            exclude_dir: Directory to exclude from cleanup
        """
        for subdir in self.issues_dir.glob("*"):
            if subdir.is_dir() and subdir != exclude_dir:
                stale_path = subdir / filename
                if stale_path.exists():
                    try:
                        stale_path.unlink()
                    except (OSError, PermissionError):
                        pass

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

        # Determine where file is located based on milestone
        if issue.milestone and issue.milestone != "backlog":
            issue_path = self.issues_dir / issue.milestone / issue.filename
        else:
            issue_path = self.issues_dir / "backlog" / issue.filename

        if issue_path.exists():
            try:
                issue_path.unlink()
            except (OSError, PermissionError):
                return False

        return True


class YAMLMilestoneRepository(MilestoneRepository):
    """Milestone repository using YAML file storage.

    This repository stores milestone files in a flat structure:

    **File Organization:**
    - All milestones stored in `.roadmap/milestones/`
    - Each milestone is one markdown file
    - No subdirectories (unlike issues)
    - Archived milestones → `.roadmap/archive/milestones/`

    **Relationship to Issues:**
    - Milestone names are used as directory names in `.roadmap/issues/{milestone_name}`
    - Deleting milestone doesn't delete associated issues (only the milestone metadata)
    - Issues maintain reference to milestone by name

    **Update Behavior:**
    - Updates do NOT move files
    - All updates saved to same file location
    - No stale file cleanup needed (flat structure)
    """

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
                    "description": milestone.content,
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
    """Project repository using YAML file storage.

    This repository stores project files in a flat structure:

    **File Organization:**
    - All projects stored in `.roadmap/projects/`
    - Each project is one markdown file
    - No subdirectories
    - Archived projects → `.roadmap/archive/projects/`

    **Update Behavior:**
    - Updates do NOT move files
    - All updates saved to same file location
    - No stale file cleanup needed (flat structure)

    **Note:** Projects are distinct from issues and milestones. They can reference
    milestones but don't affect the issue file organization.
    """

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
                    "description": project.content,
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
