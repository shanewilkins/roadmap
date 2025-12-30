"""YAML-based repository implementations.

This module provides concrete implementations of repository protocols
using YAML file storage, maintaining backward compatibility with existing
file-based storage while decoupling services from implementation details.
"""

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
from roadmap.infrastructure.file_enumeration import FileEnumerationService

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

        # Track old milestone and filename to handle file moves and renames
        old_milestone = issue.milestone
        old_filename = issue.filename  # Capture before title/other changes
        logger.debug(
            "updating_issue",
            issue_id=issue_id,
            old_milestone=old_milestone,
            old_filename=old_filename,
            update_fields=list(updates.keys()),
        )

        # Update fields
        for key, value in updates.items():
            if hasattr(issue, key):
                setattr(issue, key, value)

        # If milestone changed, move the file from old location to new location
        if "milestone" in updates and old_milestone != issue.milestone:
            # Determine old location
            if old_milestone and old_milestone != "backlog":
                old_path = self.issues_dir / old_milestone / issue.filename
            else:
                old_path = self.issues_dir / "backlog" / issue.filename

            # Determine new location
            if issue.milestone and issue.milestone != "backlog":
                new_path = self.issues_dir / issue.milestone / issue.filename
            else:
                new_path = self.issues_dir / "backlog" / issue.filename

            # Create new directory if needed
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # Move the file if it exists at old location
            if old_path.exists():
                try:
                    shutil.move(str(old_path), str(new_path))
                except (OSError, PermissionError):
                    # If move fails, just save to new location
                    IssueParser.save_issue_file(issue, new_path)
            else:
                # If file doesn't exist at old location, just save to new location
                IssueParser.save_issue_file(issue, new_path)

            # Clean up any other copies that might exist in other directories
            # This handles migration from old file locations
            for subdir in self.issues_dir.glob("*"):
                if subdir.is_dir() and subdir != new_path.parent:
                    stale_path = subdir / issue.filename
                    if stale_path.exists():
                        try:
                            stale_path.unlink()
                        except (OSError, PermissionError):
                            pass

            # Set the file_path on the issue object so it reflects the new location
            issue.file_path = str(new_path)
            logger.info(
                "issue_milestone_updated",
                issue_id=issue_id,
                old_milestone=old_milestone,
                new_milestone=issue.milestone,
                old_path=str(old_path) if old_path.exists() else None,
                new_path=str(new_path),
            )
            return issue

        # For non-milestone updates, handle filename changes (e.g., when title is updated)
        logger.debug(
            "issue_field_updated_without_milestone_change",
            issue_id=issue_id,
            old_filename=old_filename,
            new_filename=issue.filename,
            update_fields=list(updates.keys()),
        )

        # Determine the current directory
        if issue.milestone and issue.milestone != "backlog":
            target_dir = self.issues_dir / issue.milestone
        else:
            target_dir = self.issues_dir / "backlog"

        # If filename changed (e.g., due to title change), clean up the old file
        if old_filename != issue.filename:
            old_file_path = target_dir / old_filename
            if old_file_path.exists():
                try:
                    old_file_path.unlink()
                    logger.debug(
                        "removed_old_filename_after_update",
                        issue_id=issue_id,
                        old_filename=old_filename,
                        removed_path=str(old_file_path),
                    )
                except (OSError, PermissionError) as e:
                    logger.warning(
                        "failed_to_remove_old_filename_after_update",
                        issue_id=issue_id,
                        old_filename=old_filename,
                        path=str(old_file_path),
                        error=str(e),
                    )

            # Also check in other directories for the old file (in case of a race condition)
            for subdir in self.issues_dir.glob("*"):
                if subdir.is_dir():
                    stale_path = subdir / old_filename
                    if stale_path.exists():
                        try:
                            stale_path.unlink()
                            logger.debug(
                                "removed_stale_old_filename_after_update",
                                issue_id=issue_id,
                                old_filename=old_filename,
                                removed_path=str(stale_path),
                            )
                        except (OSError, PermissionError):
                            pass

        # Save the updated issue with its new filename
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
