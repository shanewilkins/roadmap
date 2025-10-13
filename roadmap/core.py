"""Core roadmap functionality."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .git_integration import GitIntegration
from .models import (
    Issue,
    IssueType,
    Milestone,
    MilestoneStatus,
    Priority,
    RoadmapConfig,
    Status,
)
from .parser import IssueParser, MilestoneParser
from .security import (
    create_secure_directory,
    create_secure_file,
    log_security_event,
    sanitize_filename,
    secure_file_permissions,
    validate_path,
)


class RoadmapCore:
    """Core roadmap functionality."""

    def __init__(
        self, root_path: Optional[Path] = None, roadmap_dir_name: str = ".roadmap"
    ):
        """Initialize roadmap core with root path and custom roadmap directory name."""
        self.root_path = root_path or Path.cwd()
        self.roadmap_dir_name = roadmap_dir_name
        self.roadmap_dir = self.root_path / roadmap_dir_name
        self.issues_dir = self.roadmap_dir / "issues"
        self.milestones_dir = self.roadmap_dir / "milestones"
        self.projects_dir = self.roadmap_dir / "projects"
        self.templates_dir = self.roadmap_dir / "templates"
        self.artifacts_dir = self.roadmap_dir / "artifacts"
        self.config_file = self.roadmap_dir / "config.yaml"

        # Initialize Git integration
        self.git = GitIntegration(self.root_path)

        # Cache for team members to avoid repeated API calls
        self._team_members_cache = None
        self._cache_timestamp = None

    def is_initialized(self) -> bool:
        """Check if roadmap is initialized in current directory."""
        return self.roadmap_dir.exists() and self.config_file.exists()

    @classmethod
    def find_existing_roadmap(
        cls, root_path: Optional[Path] = None
    ) -> Optional["RoadmapCore"]:
        """Find an existing roadmap directory in the current path.

        Searches for common roadmap directory names and returns a RoadmapCore
        instance if found, or None if no roadmap is detected.
        """
        search_path = root_path or Path.cwd()

        # Common roadmap directory names to search for
        possible_names = [".roadmap"]

        # Also check for any directory containing the expected structure
        for item in search_path.iterdir():
            if item.is_dir():
                possible_names.append(item.name)

        # Check each possible directory
        for dir_name in possible_names:
            potential_core = cls(root_path=search_path, roadmap_dir_name=dir_name)
            if potential_core.is_initialized():
                return potential_core

        return None

    def initialize(self) -> None:
        """Initialize a new roadmap in the current directory."""
        if self.is_initialized():
            raise ValueError("Roadmap already initialized in this directory")

        # Create directory structure with secure permissions
        create_secure_directory(
            self.roadmap_dir, 0o755
        )  # Owner full, group/other read/execute
        create_secure_directory(self.issues_dir, 0o755)
        create_secure_directory(self.milestones_dir, 0o755)
        create_secure_directory(self.projects_dir, 0o755)
        create_secure_directory(self.templates_dir, 0o755)
        create_secure_directory(self.artifacts_dir, 0o755)

        # Update .gitignore to exclude roadmap local data
        self._update_gitignore()

        # Copy templates
        self._create_default_templates()

        # Create default config
        config = RoadmapConfig()
        config.save_to_file(self.config_file)

    def _create_default_templates(self) -> None:
        """Create default templates."""
        # Issue template
        issue_template = """---
id: "{{ issue_id }}"
title: "{{ title }}"
priority: "medium"
status: "todo"
milestone: ""
labels: []
github_issue: null
created: "{{ created_date }}"
updated: "{{ updated_date }}"
assignee: ""
---

# {{ title }}

## Description

Brief description of the issue or feature request.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Notes

Any technical details, considerations, or implementation notes.

## Related Issues

- Links to related issues
- Dependencies

## Additional Context

Any additional context, screenshots, or examples."""

        with create_secure_file(self.templates_dir / "issue.md", "w", 0o644) as f:
            f.write(issue_template)

        # Milestone template
        milestone_template = """---
name: "{{ milestone_name }}"
description: "{{ description }}"
due_date: "{{ due_date }}"
status: "open"
github_milestone: null
created: "{{ created_date }}"
updated: "{{ updated_date }}"
---

# {{ milestone_name }}

## Description

{{ description }}

## Goals

- [ ] Goal 1
- [ ] Goal 2
- [ ] Goal 3

## Success Criteria

Define what success looks like for this milestone.

## Notes

Any additional notes or considerations for this milestone."""

        with create_secure_file(
            self.templates_dir / "milestone.md", "w", 0o644
        ) as f:
            f.write(milestone_template)

        # Project template
        project_template = """---
id: "{{ project_id }}"
name: "{{ project_name }}"
description: "{{ project_description }}"
status: "planning"
priority: "medium"
owner: "{{ project_owner }}"
start_date: "{{ start_date }}"
target_end_date: "{{ target_end_date }}"
actual_end_date: null
created: "{{ created_date }}"
updated: "{{ updated_date }}"
milestones:
  - "{{ milestone_1 }}"
  - "{{ milestone_2 }}"
estimated_hours: {{ estimated_hours }}
actual_hours: null
---

# {{ project_name }}

## Project Overview

{{ project_description }}

**Project Owner:** {{ project_owner }}
**Status:** {{ status }}
**Timeline:** {{ start_date }} → {{ target_end_date }}

## Objectives

- [ ] Objective 1
- [ ] Objective 2
- [ ] Objective 3

## Milestones & Timeline

{% for milestone in milestones %}
- **{{ milestone }}** - [Link to milestone](../milestones/{{ milestone }}.md)
{% endfor %}

## Timeline Tracking

- **Start Date:** {{ start_date }}
- **Target End Date:** {{ target_end_date }}
- **Actual End Date:** {{ actual_end_date }}
- **Estimated Hours:** {{ estimated_hours }}
- **Actual Hours:** {{ actual_hours }}

## Notes

Project notes and additional context.

---
*Last updated: {{ updated_date }}*"""

        with create_secure_file(
            self.templates_dir / "project.md", "w", 0o644
        ) as f:
            f.write(project_template)

    def _update_gitignore(self) -> None:
        """Update .gitignore to exclude roadmap local data from version control."""
        gitignore_path = self.root_path / ".gitignore"

        # Define patterns to ignore relative to project root
        roadmap_patterns = [
            f"{self.roadmap_dir_name}/artifacts/",
            f"{self.roadmap_dir_name}/backups/", 
            f"{self.roadmap_dir_name}/*.tmp",
            f"{self.roadmap_dir_name}/*.lock"
        ]
        gitignore_comment = f"# Roadmap local data (generated exports, backups, temp files)"

        # Read existing .gitignore if it exists
        existing_lines = []
        if gitignore_path.exists():
            existing_lines = gitignore_path.read_text().splitlines()

        # Check which patterns are already present
        missing_patterns = []
        for pattern in roadmap_patterns:
            if not any(line.strip() == pattern for line in existing_lines):
                missing_patterns.append(pattern)

        if missing_patterns:
            # Add missing patterns to .gitignore
            if existing_lines and not existing_lines[-1].strip() == "":
                existing_lines.append("")  # Add blank line if needed

            existing_lines.append(gitignore_comment)
            existing_lines.extend(missing_patterns)

            # Write updated .gitignore
            gitignore_path.write_text("\n".join(existing_lines) + "\n")

    def load_config(self) -> RoadmapConfig:
        """Load roadmap configuration."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        return RoadmapConfig.load_from_file(self.config_file)

    def create_issue(
        self,
        title: str,
        priority: Priority = Priority.MEDIUM,
        issue_type: IssueType = IssueType.OTHER,
        milestone: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        estimated_hours: Optional[float] = None,
        depends_on: Optional[List[str]] = None,
        blocks: Optional[List[str]] = None,
    ) -> Issue:
        """Create a new issue."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        issue = Issue(
            title=title,
            priority=priority,
            issue_type=issue_type,
            milestone=milestone or "",
            labels=labels or [],
            assignee=assignee,
            estimated_hours=estimated_hours,
            depends_on=depends_on or [],
            blocks=blocks or [],
            content=f"# {title}\n\n## Description\n\nBrief description of the issue or feature request.\n\n## Acceptance Criteria\n\n- [ ] Criterion 1\n- [ ] Criterion 2\n- [ ] Criterion 3",
        )

        issue_path = self.issues_dir / issue.filename
        IssueParser.save_issue_file(issue, issue_path)

        return issue

    def list_issues(
        self,
        milestone: Optional[str] = None,
        status: Optional[Status] = None,
        priority: Optional[Priority] = None,
        issue_type: Optional[IssueType] = None,
        assignee: Optional[str] = None,
    ) -> List[Issue]:
        """List issues with optional filtering."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        issues = []
        for issue_file in self.issues_dir.glob("*.md"):
            try:
                issue = IssueParser.parse_issue_file(issue_file)

                # Apply filters
                if milestone and issue.milestone != milestone:
                    continue
                if status and issue.status != status:
                    continue
                if priority and issue.priority != priority:
                    continue
                if issue_type and issue.issue_type != issue_type:
                    continue
                if assignee and issue.assignee != assignee:
                    continue
                if priority and issue.priority != priority:
                    continue
                if assignee and issue.assignee != assignee:
                    continue

                issues.append(issue)
            except Exception as e:
                # Skip malformed files
                continue

        # Sort by priority then by creation date
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }
        issues.sort(key=lambda x: (priority_order.get(x.priority, 999), x.created))

        return issues

    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Get a specific issue by ID."""
        for issue_file in self.issues_dir.glob(f"{issue_id}-*.md"):
            try:
                return IssueParser.parse_issue_file(issue_file)
            except Exception:
                continue
        return None

    def update_issue(self, issue_id: str, **updates) -> Optional[Issue]:
        """Update an existing issue."""
        issue = self.get_issue(issue_id)
        if not issue:
            return None

        # Update fields
        for field, value in updates.items():
            if hasattr(issue, field):
                setattr(issue, field, value)

        # Update timestamp
        issue.updated = datetime.now()

        # Save updated issue
        issue_path = self.issues_dir / issue.filename
        IssueParser.save_issue_file(issue, issue_path)

        return issue

    def delete_issue(self, issue_id: str) -> bool:
        """Delete an issue."""
        for issue_file in self.issues_dir.glob(f"{issue_id}-*.md"):
            try:
                issue_file.unlink()
                return True
            except Exception:
                continue
        return False

    def create_milestone(
        self, name: str, description: str = "", due_date: Optional[datetime] = None
    ) -> Milestone:
        """Create a new milestone."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        milestone = Milestone(
            name=name,
            description=description,
            due_date=due_date,
            content=f"# {name}\n\n## Description\n\n{description}\n\n## Goals\n\n- [ ] Goal 1\n- [ ] Goal 2\n- [ ] Goal 3",
        )

        milestone_path = self.milestones_dir / milestone.filename
        MilestoneParser.save_milestone_file(milestone, milestone_path)

        return milestone

    def list_milestones(self) -> List[Milestone]:
        """List all milestones."""
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized. Run 'roadmap init' first.")

        milestones = []
        for milestone_file in self.milestones_dir.glob("*.md"):
            try:
                milestone = MilestoneParser.parse_milestone_file(milestone_file)
                milestones.append(milestone)
            except Exception:
                continue

        milestones.sort(key=lambda x: x.created)
        return milestones

    def get_milestone(self, name: str) -> Optional[Milestone]:
        """Get a specific milestone by name."""
        safe_name = "".join(
            c for c in name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_name = safe_name.replace(" ", "-").lower()

        milestone_file = self.milestones_dir / f"{safe_name}.md"
        if milestone_file.exists():
            try:
                return MilestoneParser.parse_milestone_file(milestone_file)
            except Exception:
                pass
        return None

    def delete_milestone(self, name: str) -> bool:
        """Delete a milestone and unassign all issues from it.

        Args:
            name: Name of the milestone to delete

        Returns:
            True if milestone was deleted, False if not found
        """
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized")

        # Check if milestone exists
        milestone = self.get_milestone(name)
        if not milestone:
            return False

        # Unassign all issues from this milestone
        issues = self.list_issues(milestone=name)
        for issue in issues:
            issue.milestone = None
            issue.updated = datetime.now()
            issue_path = self.issues_dir / issue.filename
            IssueParser.save_issue_file(issue, issue_path)

        # Delete the milestone file
        safe_name = "".join(
            c for c in name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_name = safe_name.replace(" ", "-").lower()
        milestone_file = self.milestones_dir / f"{safe_name}.md"

        try:
            milestone_file.unlink()
            return True
        except Exception:
            return False

    def update_milestone(
        self,
        name: str,
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        clear_due_date: bool = False,
        status: Optional[str] = None,
    ) -> bool:
        """Update a milestone's properties.

        Args:
            name: Name of the milestone to update
            description: New description (None to keep current)
            due_date: New due date (None to keep current)
            clear_due_date: If True, remove the due date
            status: New status (None to keep current)

        Returns:
            True if milestone was updated, False if not found
        """
        if not self.is_initialized():
            raise ValueError("Roadmap not initialized")

        # Get the existing milestone
        milestone = self.get_milestone(name)
        if not milestone:
            return False

        # Update fields if provided
        if description is not None:
            milestone.description = description

        if clear_due_date:
            milestone.due_date = None
        elif due_date is not None:
            milestone.due_date = due_date

        if status is not None:
            milestone.status = status

        milestone.updated = datetime.now()

        # Save the updated milestone
        safe_name = "".join(
            c for c in name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_name = safe_name.replace(" ", "-").lower()
        milestone_file = self.milestones_dir / f"{safe_name}.md"

        try:
            MilestoneParser.save_milestone_file(milestone, milestone_file)
            return True
        except Exception:
            return False

    def assign_issue_to_milestone(self, issue_id: str, milestone_name: str) -> bool:
        """Assign an issue to a milestone."""
        issue = self.get_issue(issue_id)
        if not issue:
            return False

        milestone = self.get_milestone(milestone_name)
        if not milestone:
            return False

        issue.milestone = milestone_name
        issue.updated = datetime.now()

        issue_path = self.issues_dir / issue.filename
        IssueParser.save_issue_file(issue, issue_path)

        return True

    def get_milestone_progress(self, milestone_name: str) -> Dict[str, Any]:
        """Get progress statistics for a milestone."""
        issues = self.list_issues(milestone=milestone_name)

        if not issues:
            return {"total": 0, "completed": 0, "progress": 0.0, "by_status": {}}

        total = len(issues)
        completed = len([i for i in issues if i.status == Status.DONE])
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

    def get_backlog_issues(self) -> List[Issue]:
        """Get all issues not assigned to any milestone (backlog)."""
        all_issues = self.list_issues()
        return [issue for issue in all_issues if issue.is_backlog]

    def get_milestone_issues(self, milestone_name: str) -> List[Issue]:
        """Get all issues assigned to a specific milestone."""
        all_issues = self.list_issues()
        return [issue for issue in all_issues if issue.milestone == milestone_name]

    def get_issues_by_milestone(self) -> Dict[str, List[Issue]]:
        """Get all issues grouped by milestone, including backlog."""
        all_issues = self.list_issues()
        grouped = {"Backlog": []}

        # Add backlog issues
        for issue in all_issues:
            if issue.is_backlog:
                grouped["Backlog"].append(issue)
            else:
                milestone_name = issue.milestone
                if milestone_name not in grouped:
                    grouped[milestone_name] = []
                grouped[milestone_name].append(issue)

        return grouped

    def move_issue_to_milestone(
        self, issue_id: str, milestone_name: Optional[str]
    ) -> bool:
        """Move an issue to a milestone or to backlog if milestone_name is None."""
        issue = self.get_issue(issue_id)
        if not issue:
            return False

        # Validate milestone exists if provided
        if milestone_name and not self.get_milestone(milestone_name):
            return False

        # Update issue milestone
        issue.milestone = milestone_name
        issue.updated = datetime.now()

        # Save updated issue
        issue_path = self.issues_dir / issue.filename
        IssueParser.save_issue_file(issue, issue_path)

        return True

    def get_next_milestone(self) -> Optional[Milestone]:
        """Get the next upcoming milestone based on due date."""
        milestones = self.list_milestones()

        # Filter for open milestones with due dates
        upcoming_milestones = [
            m
            for m in milestones
            if m.status == MilestoneStatus.OPEN and m.due_date is not None
        ]

        if not upcoming_milestones:
            return None

        # Sort by due date and return the earliest
        upcoming_milestones.sort(key=lambda x: x.due_date)
        return upcoming_milestones[0]

    def _get_github_config(self) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Get GitHub configuration from config file and credentials.
        
        Returns:
            Tuple of (token, owner, repo) or (None, None, None) if not configured
        """
        try:
            from .credentials import get_credential_manager
            
            config = self.load_config()
            github_config = config.github or {}
            
            # Get owner and repo from config
            owner = github_config.get("owner")
            repo = github_config.get("repo")
            
            if not owner or not repo:
                return None, None, None
                
            # Get token from credentials manager or environment
            credential_manager = get_credential_manager()
            token = credential_manager.get_credential("github", "token")
            
            if not token:
                import os
                token = os.getenv("GITHUB_TOKEN")
                
            return token, owner, repo
            
        except Exception:
            return None, None, None

    def get_team_members(self) -> List[str]:
        """Get team members from GitHub repository.

        Returns:
            List of usernames if GitHub is configured, empty list otherwise
        """
        try:
            from .github_client import GitHubClient

            token, owner, repo = self._get_github_config()
            if not token or not owner or not repo:
                return []

            # Get team members
            client = GitHubClient(token=token, owner=owner, repo=repo)
            return client.get_team_members()
        except Exception:
            # Return empty list if GitHub is not configured or accessible
            return []

    def get_current_user(self) -> Optional[str]:
        """Get the current GitHub user.

        Returns:
            Current user's GitHub username if configured, None otherwise
        """
        try:
            from .github_client import GitHubClient

            token, owner, repo = self._get_github_config()
            if not token or not owner or not repo:
                return None

            # Get current user
            client = GitHubClient(token=token, owner=owner, repo=repo)
            return client.get_current_user()
        except Exception:
            # Return None if GitHub is not configured or accessible
            return None

    def get_assigned_issues(self, assignee: str) -> List[Issue]:
        """Get all issues assigned to a specific user."""
        return self.list_issues(assignee=assignee)

    def get_my_issues(self) -> List[Issue]:
        """Get all issues assigned to the current user."""
        current_user = self.get_current_user()
        if not current_user:
            return []
        return self.get_assigned_issues(current_user)

    def get_all_assigned_issues(self) -> Dict[str, List[Issue]]:
        """Get all issues grouped by assignee.

        Returns:
            Dictionary mapping assignee usernames to their assigned issues
        """
        all_issues = self.list_issues()
        assigned_issues = {}

        for issue in all_issues:
            if issue.assignee:
                if issue.assignee not in assigned_issues:
                    assigned_issues[issue.assignee] = []
                assigned_issues[issue.assignee].append(issue)

        return assigned_issues

    def _get_cached_team_members(self) -> List[str]:
        """Get team members with caching (5 minute cache)."""
        from datetime import datetime, timedelta
        
        # Check if cache is valid (5 minutes)
        if (self._team_members_cache is not None and 
            self._cache_timestamp is not None and 
            datetime.now() - self._cache_timestamp < timedelta(minutes=5)):
            return self._team_members_cache
            
        # Refresh cache
        team_members = self.get_team_members()
        self._team_members_cache = team_members
        self._cache_timestamp = datetime.now()
        
        return team_members

    def validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Validate an assignee against GitHub repository access.
        
        This validation only occurs when GitHub integration is configured.
        For local-only roadmaps, any assignee name is allowed without validation.
        
        Args:
            assignee: Username to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if valid or GitHub not configured  
            - (False, error_message) if invalid GitHub user
        """
        if not assignee or not assignee.strip():
            return False, "Assignee cannot be empty"

        assignee = assignee.strip()

        try:
            token, owner, repo = self._get_github_config()
            if not token or not owner or not repo:
                # If GitHub is not configured, allow any assignee without validation
                # This supports local-only roadmap usage without GitHub integration
                return True, ""

            # GitHub is configured - perform validation against repository access
            
            # First check against cached team members for performance
            team_members = self._get_cached_team_members()
            if team_members and assignee in team_members:
                return True, ""
            
            # If not in cache or cache is empty, do full validation via API
            from .github_client import GitHubClient
            
            client = GitHubClient(token=token, owner=owner, repo=repo)
            
            # This will do the full GitHub API validation
            return client.validate_assignee(assignee)

        except Exception as e:
            # If validation fails due to network/API issues, allow the assignment
            # but log a warning that validation couldn't be performed
            return True, f"Warning: Could not validate assignee (GitHub API unavailable): {str(e)}"

    # Git Integration Methods

    def get_git_context(self) -> Dict[str, Any]:
        """Get Git repository context information."""
        if not self.git.is_git_repository():
            return {"is_git_repo": False}

        context = {"is_git_repo": True}
        context.update(self.git.get_repository_info())

        # Current branch info
        current_branch = self.git.get_current_branch()
        if current_branch:
            context["current_branch"] = current_branch.name

            # Try to find linked issue
            issue_id = current_branch.extract_issue_id()
            if issue_id:
                issue = self.get_issue(issue_id)
                if issue:
                    context["linked_issue"] = {
                        "id": issue.id,
                        "title": issue.title,
                        "status": issue.status.value,
                        "priority": issue.priority.value,
                    }

        return context

    def get_current_user_from_git(self) -> Optional[str]:
        """Get current user from Git configuration."""
        return self.git.get_current_user()

    def create_issue_with_git_branch(self, title: str, **kwargs) -> Optional[Issue]:
        """Create an issue and optionally create a Git branch for it."""
        # Create the issue first
        issue = self.create_issue(title, **kwargs)
        if not issue:
            return None

        # If we're in a Git repo and auto_create_branch is requested
        if kwargs.get("auto_create_branch", False) and self.git.is_git_repository():
            self.git.create_branch_for_issue(
                issue, checkout=kwargs.get("checkout_branch", True)
            )

        return issue

    def link_issue_to_current_branch(self, issue_id: str) -> bool:
        """Link an issue to the current Git branch."""
        if not self.git.is_git_repository():
            return False

        current_branch = self.git.get_current_branch()
        if not current_branch:
            return False

        issue = self.get_issue(issue_id)
        if not issue:
            return False

        # Add branch information to issue metadata
        if not hasattr(issue, "git_branches"):
            issue.git_branches = []

        if current_branch.name not in issue.git_branches:
            issue.git_branches.append(current_branch.name)

        # Update the issue
        return self.update_issue(issue_id, git_branches=issue.git_branches) is not None

    def get_commits_for_issue(self, issue_id: str, since: Optional[str] = None) -> List:
        """Get Git commits that reference this issue."""
        if not self.git.is_git_repository():
            return []

        return self.git.get_commits_for_issue(issue_id, since)

    def update_issue_from_git_activity(self, issue_id: str) -> bool:
        """Update issue progress and status based on Git commit activity."""
        if not self.git.is_git_repository():
            return False

        commits = self.get_commits_for_issue(issue_id)
        if not commits:
            return False

        # Get the most recent commit with roadmap updates
        latest_updates = {}
        for commit in commits:
            updates = self.git.parse_commit_message_for_updates(commit)
            if updates:
                latest_updates.update(updates)

        if latest_updates:
            # Update the issue with the extracted information
            self.update_issue(issue_id, **latest_updates)
            return True

        return False

    def suggest_branch_name_for_issue(self, issue_id: str) -> Optional[str]:
        """Suggest a branch name for an issue."""
        issue = self.get_issue(issue_id)
        if not issue or not self.git.is_git_repository():
            return None

        return self.git.suggest_branch_name(issue)

    def get_branch_linked_issues(self) -> Dict[str, List[str]]:
        """Get mapping of branches to their linked issue IDs."""
        if not self.git.is_git_repository():
            return {}

        branches = self.git.get_all_branches()
        branch_issues = {}

        for branch in branches:
            issue_id = branch.extract_issue_id()
            if issue_id and self.get_issue(issue_id):
                branch_issues[branch.name] = [issue_id]

        return branch_issues

    def _generate_id(self) -> str:
        """Generate a unique ID for projects and issues."""
        import uuid
        return str(uuid.uuid4()).replace('-', '')[:8]

    def _normalize_filename(self, title: str) -> str:
        """Normalize a title for use as a filename."""
        import re
        # Replace non-alphanumeric characters with hyphens
        normalized = re.sub(r'[^a-zA-Z0-9\s]', '', title)
        # Replace spaces with hyphens and convert to lowercase
        normalized = re.sub(r'\s+', '-', normalized.strip()).lower()
        # Remove consecutive hyphens
        normalized = re.sub(r'-+', '-', normalized)
        # Remove leading/trailing hyphens
        return normalized.strip('-')
