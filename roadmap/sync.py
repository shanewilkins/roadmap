"""Synchronization module for GitHub integration."""

import os
from datetime import datetime
from enum import Enum
from typing import Any

from .core import RoadmapCore
from .credentials import CredentialManagerError, get_credential_manager, mask_token
from .datetime_parser import parse_github_datetime
from .github_client import GitHubAPIError, GitHubClient
from .models import Issue, Milestone, MilestoneStatus, Priority, RoadmapConfig, Status
from .parser import IssueParser, MilestoneParser


class SyncConflictStrategy(Enum):
    """Strategies for handling sync conflicts."""

    LOCAL_WINS = "local_wins"  # Always prefer local version
    REMOTE_WINS = "remote_wins"  # Always prefer remote version
    NEWER_WINS = "newer_wins"  # Use timestamp comparison
    INTERACTIVE = "interactive"  # Prompt user for resolution


class SyncConflict:
    """Represents a sync conflict between local and remote items."""

    def __init__(
        self,
        item_type: str,
        item_id: str,
        local_item: Issue | Milestone,
        remote_item: dict,
        local_updated: datetime,
        remote_updated: datetime,
    ):
        self.item_type = item_type  # "issue" or "milestone"
        self.item_id = item_id
        self.local_item = local_item
        self.remote_item = remote_item
        self.local_updated = local_updated
        self.remote_updated = remote_updated

    def get_newer_item(self) -> str:
        """Determine which item is newer based on timestamps."""
        # Normalize both timestamps to UTC for comparison
        local_updated = self.local_updated
        remote_updated = self.remote_updated

        # Convert to UTC if timezone naive
        if local_updated.tzinfo is None:
            from datetime import timezone

            local_updated = local_updated.replace(tzinfo=timezone.utc)

        if remote_updated.tzinfo is None:
            from datetime import timezone

            remote_updated = remote_updated.replace(tzinfo=timezone.utc)

        # Convert both to UTC for comparison
        local_utc = (
            local_updated.astimezone(timezone.utc)
            if local_updated.tzinfo
            else local_updated
        )
        remote_utc = (
            remote_updated.astimezone(timezone.utc)
            if remote_updated.tzinfo
            else remote_updated
        )

        if local_utc > remote_utc:
            return "local"
        elif remote_utc > local_utc:
            return "remote"
        else:
            return "same"


class SyncStrategy:
    """Handles conflict resolution and synchronization strategies."""

    def __init__(
        self, strategy: SyncConflictStrategy = SyncConflictStrategy.LOCAL_WINS
    ):
        # Default to LOCAL_WINS to avoid GitHub timestamp race conditions:
        # When we push local changes to GitHub, GitHub updates its updated_at timestamp,
        # causing subsequent bidirectional syncs with NEWER_WINS to prefer GitHub
        # and potentially override the local changes we just pushed.
        self.strategy = strategy
        self.conflicts_found: list[SyncConflict] = []

    def _parse_github_timestamp(self, github_timestamp: str) -> datetime:
        """Safely parse GitHub timestamp, handling both Z and +00:00 formats."""
        if not github_timestamp:
            return datetime.min

        # Handle malformed timestamps from tests (e.g., "2025-01-01T00:00:00+00:00Z")
        return parse_github_datetime(github_timestamp)

    def compare_timestamps(
        self, local_updated: datetime, github_updated_str: str
    ) -> str:
        """Compare local and GitHub timestamps.

        Args:
            local_updated: Local item's updated timestamp
            github_updated_str: GitHub's updated_at timestamp string

        Returns:
            "local_newer", "remote_newer", or "same"
        """
        try:
            # Parse GitHub timestamp (ISO format)
            remote_updated = parse_github_datetime(github_updated_str)

            # Convert local timestamp to UTC if it's naive
            if local_updated.tzinfo is None:
                # Assume local naive datetime is UTC
                from datetime import timezone

                local_updated = local_updated.replace(tzinfo=timezone.utc)

            # Convert remote to same timezone as local for comparison
            if remote_updated.tzinfo != local_updated.tzinfo:
                remote_updated = remote_updated.astimezone(local_updated.tzinfo)

            # Compare timestamps
            if local_updated > remote_updated:
                return "local_newer"
            elif remote_updated > local_updated:
                return "remote_newer"
            else:
                return "same"

        except (ValueError, AttributeError):
            # If we can't parse the timestamp, assume remote is newer
            return "remote_newer"

    def detect_issue_conflict(
        self, local_issue: Issue, github_issue: dict
    ) -> SyncConflict | None:
        """Detect if there's a conflict between local and GitHub issue."""
        local_updated = local_issue.updated
        github_updated = github_issue.get("updated_at", "")

        comparison = self.compare_timestamps(local_updated, github_updated)

        if comparison != "same":
            # There's a time difference - this could be a conflict
            conflict = SyncConflict(
                item_type="issue",
                item_id=str(local_issue.github_issue or local_issue.id),
                local_item=local_issue,
                remote_item=github_issue,
                local_updated=local_updated,
                remote_updated=self._parse_github_timestamp(github_updated),
            )
            return conflict

        return None

    def detect_milestone_conflict(
        self, local_milestone: Milestone, github_milestone: dict
    ) -> SyncConflict | None:
        """Detect if there's a conflict between local and GitHub milestone."""
        local_updated = local_milestone.updated
        github_updated = github_milestone.get("updated_at", "")

        comparison = self.compare_timestamps(local_updated, github_updated)

        if comparison != "same":
            conflict = SyncConflict(
                item_type="milestone",
                item_id=str(local_milestone.github_milestone or local_milestone.name),
                local_item=local_milestone,
                remote_item=github_milestone,
                local_updated=local_updated,
                remote_updated=self._parse_github_timestamp(github_updated),
            )
            return conflict

        return None

    def resolve_conflict(self, conflict: SyncConflict) -> str:
        """Resolve a conflict based on the strategy.

        Returns:
            "use_local", "use_remote", or "skip"
        """
        if self.strategy == SyncConflictStrategy.LOCAL_WINS:
            return "use_local"
        elif self.strategy == SyncConflictStrategy.REMOTE_WINS:
            return "use_remote"
        elif self.strategy == SyncConflictStrategy.NEWER_WINS:
            newer = conflict.get_newer_item()
            if newer == "local":
                return "use_local"
            elif newer == "remote":
                return "use_remote"
            else:
                return "use_local"  # Default to local if same timestamp
        elif self.strategy == SyncConflictStrategy.INTERACTIVE:
            # For now, default to newer wins (interactive will be implemented in CLI)
            return self.resolve_conflict(
                SyncConflict(
                    conflict.item_type,
                    conflict.item_id,
                    conflict.local_item,
                    conflict.remote_item,
                    conflict.local_updated,
                    conflict.remote_updated,
                )
            )

        return "skip"


class SyncManager:
    """Manages synchronization between local roadmap and GitHub repository."""

    def __init__(
        self,
        core: RoadmapCore,
        config: RoadmapConfig,
        sync_strategy: SyncConflictStrategy = SyncConflictStrategy.LOCAL_WINS,
    ):
        """Initialize sync manager.

        Default sync strategy is LOCAL_WINS to prevent GitHub timestamp race conditions
        where pushing local changes updates GitHub's timestamp, causing subsequent
        bidirectional syncs to prefer remote and override local changes.
        """
        self.core = core
        self.config = config
        self.github_client = None
        self.sync_strategy = SyncStrategy(sync_strategy)

        # Initialize GitHub client if configured
        self._init_github_client()

    def _init_github_client(self) -> None:
        """Initialize GitHub client from configuration."""
        github_config = self.config.github

        if not github_config:
            return

        # Get token from multiple sources with priority:
        # 1. Configuration file (for backward compatibility)
        # 2. Environment variable
        # 3. Credential manager
        token = self._get_token_secure(github_config)
        owner = github_config.get("owner")
        repo = github_config.get("repo")

        if token and owner and repo:
            try:
                self.github_client = GitHubClient(token=token, owner=owner, repo=repo)
            except GitHubAPIError:
                # Client initialization failed, will be handled when needed
                pass
        elif not token:
            # Explicitly don't create client if no token available
            self.github_client = None

    def _get_token_secure(self, github_config: dict) -> str | None:
        """Get token from secure sources.

        Priority order:
        1. Environment variable (GITHUB_TOKEN)
        2. Credential manager
        3. Configuration file (legacy - with deprecation warning)
        """
        # Check environment variable first (highest priority)
        env_token = os.getenv("GITHUB_TOKEN")
        if env_token:
            return env_token

        # Check credential manager second
        try:
            credential_manager = get_credential_manager()
            if credential_manager.is_available():
                stored_token = credential_manager.get_token()
                if stored_token:
                    return stored_token
        except Exception:
            pass

        # Check configuration file last (legacy with warning)
        config_token = github_config.get("token")
        if config_token:
            # TODO: Add deprecation warning in future version
            # print("⚠️ Token stored in config file is deprecated. Use 'roadmap sync setup --secure' to migrate to secure storage.")
            return config_token

        return None

    def is_configured(self) -> bool:
        """Check if GitHub integration is configured."""
        return self.github_client is not None

    def store_token_secure(
        self, token: str, repo_info: dict[str, str] | None = None
    ) -> tuple[bool, str]:
        """Store GitHub token securely using credential manager.

        Args:
            token: GitHub personal access token
            repo_info: Optional repository information

        Returns:
            Tuple of (success, message)
        """
        try:
            credential_manager = get_credential_manager()

            if not credential_manager.is_available():
                return (
                    False,
                    "Secure credential storage not available on this system. Token will be stored in config file or use GITHUB_TOKEN environment variable.",
                )

            success = credential_manager.store_token(token, repo_info)
            if success:
                return (
                    True,
                    f"Token stored securely in system credential manager. Masked token: {mask_token(token)}",
                )
            else:
                return False, "Failed to store token in credential manager."

        except CredentialManagerError as e:
            return False, f"Credential manager error: {e}"
        except Exception as e:
            return False, f"Unexpected error storing token: {e}"

    def delete_token_secure(self) -> tuple[bool, str]:
        """Delete stored GitHub token from credential manager.

        Returns:
            Tuple of (success, message)
        """
        try:
            credential_manager = get_credential_manager()

            if not credential_manager.is_available():
                return False, "Secure credential storage not available on this system."

            success = credential_manager.delete_token()
            if success:
                return True, "Token deleted from credential manager."
            else:
                return (
                    False,
                    "Token not found in credential manager or deletion failed.",
                )

        except CredentialManagerError as e:
            return False, f"Credential manager error: {e}"
        except Exception as e:
            return False, f"Unexpected error deleting token: {e}"

    def get_token_info(self) -> dict[str, Any]:
        """Get information about stored tokens.

        Returns:
            Dictionary with token source information
        """
        info = {
            "config_file": bool(self.config.github.get("token")),
            "environment": bool(os.getenv("GITHUB_TOKEN")),
            "credential_manager": False,
            "credential_manager_available": False,
            "active_source": None,
            "masked_token": None,
        }

        try:
            credential_manager = get_credential_manager()
            info["credential_manager_available"] = credential_manager.is_available()

            if credential_manager.is_available():
                stored_token = credential_manager.get_token()
                info["credential_manager"] = bool(stored_token)
        except Exception:
            pass

        # Determine active source
        token = self._get_token_secure(self.config.github)
        if token:
            info["masked_token"] = mask_token(token)

            if self.config.github.get("token"):
                info["active_source"] = "config_file"
            elif os.getenv("GITHUB_TOKEN"):
                info["active_source"] = "environment"
            else:
                info["active_source"] = "credential_manager"

        return info

    def test_connection(self) -> tuple[bool, str]:
        """Test GitHub connection and authentication."""
        if not self.github_client:
            return False, "GitHub client not configured. Check config.yaml settings."

        try:
            # Test authentication
            user_info = self.github_client.test_authentication()

            # Test repository access
            repo_info = self.github_client.test_repository_access()

            return (
                True,
                f"Connected as {user_info['login']} to {repo_info['full_name']}",
            )

        except GitHubAPIError as e:
            return False, str(e)

    def setup_repository(self) -> tuple[bool, str]:
        """Set up repository with default labels and configuration."""
        if not self.github_client:
            return False, "GitHub client not configured."

        try:
            # Set up default labels
            self.github_client.setup_default_labels()
            return True, "Repository set up successfully with default labels."

        except GitHubAPIError as e:
            return False, f"Failed to set up repository: {e}"

    def push_issue(
        self, issue: Issue, check_conflicts: bool = False
    ) -> tuple[bool, str, int | None]:
        """Push a local issue to GitHub with optional conflict detection."""
        if not self.github_client:
            return False, "GitHub client not configured.", None

        try:
            # Check if issue already exists on GitHub
            if issue.github_issue:
                # If conflict checking is enabled, check for conflicts first
                if check_conflicts:
                    try:
                        github_issue = self.github_client.get_issue(issue.github_issue)
                        conflict = self.sync_strategy.detect_issue_conflict(
                            issue, github_issue
                        )

                        if conflict:
                            resolution = self.sync_strategy.resolve_conflict(conflict)
                            if resolution == "use_remote":
                                return (
                                    False,
                                    "Conflict detected: Remote version is newer. Use pull to get remote changes.",
                                    None,
                                )
                            elif resolution == "skip":
                                return (
                                    False,
                                    "Conflict detected: Skipping update due to sync strategy.",
                                    None,
                                )
                            # If "use_local", continue with update
                    except GitHubAPIError:
                        # If we can't get the GitHub issue, proceed with update
                        pass

                return self.update_github_issue(issue)

            # Create new GitHub issue
            labels = []
            labels.extend(self.github_client.priority_to_labels(issue.priority))
            labels.extend(self.github_client.status_to_labels(issue.status))
            labels.extend(issue.labels)

            # Find milestone number if assigned
            milestone_number = None
            if issue.milestone:
                milestone_number = self._find_github_milestone(issue.milestone)

            # Create issue body from content
            body = issue.content

            # Add metadata to body
            body += "\n\n---\n*Created by roadmap CLI*"

            # Prepare assignees list for GitHub API
            assignees = []
            if issue.assignee:
                assignees = [issue.assignee]

            github_issue = self.github_client.create_issue(
                title=issue.title,
                body=body,
                labels=labels,
                milestone=milestone_number,
                assignees=assignees,
            )

            # Update local issue with GitHub issue number
            issue.github_issue = github_issue["number"]
            issue.updated = datetime.now()

            # Save updated issue
            issue_path = self.core.issues_dir / issue.filename
            IssueParser.save_issue_file(issue, issue_path)

            return (
                True,
                f"Created GitHub issue #{github_issue['number']}",
                github_issue["number"],
            )

        except GitHubAPIError as e:
            return False, f"Failed to create GitHub issue: {e}", None

    def update_github_issue(self, issue: Issue) -> tuple[bool, str, int | None]:
        """Update an existing GitHub issue."""
        if not self.github_client or not issue.github_issue:
            return False, "GitHub client not configured or issue not linked.", None

        try:
            labels = []
            labels.extend(self.github_client.priority_to_labels(issue.priority))
            labels.extend(self.github_client.status_to_labels(issue.status))
            labels.extend(issue.labels)

            # Find milestone number if assigned
            milestone_number = None
            if issue.milestone:
                milestone_number = self._find_github_milestone(issue.milestone)

            # Prepare assignees list for GitHub API
            assignees = []
            if issue.assignee:
                assignees = [issue.assignee]

            # Determine state based on status
            state = "closed" if issue.status == Status.DONE else "open"

            github_issue = self.github_client.update_issue(
                issue_number=issue.github_issue,
                title=issue.title,
                body=issue.content,
                state=state,
                labels=labels,
                assignees=assignees,
                milestone=milestone_number,
            )

            # Update local issue timestamp
            issue.updated = datetime.now()
            issue_path = self.core.issues_dir / issue.filename
            IssueParser.save_issue_file(issue, issue_path)

            return (
                True,
                f"Updated GitHub issue #{issue.github_issue}",
                issue.github_issue,
            )

        except GitHubAPIError as e:
            return False, f"Failed to update GitHub issue: {e}", None

    def pull_issue(
        self, github_issue_number: int, check_conflicts: bool = False
    ) -> tuple[bool, str, Issue | None]:
        """Pull a GitHub issue and create/update local issue with optional conflict detection."""
        if not self.github_client:
            return False, "GitHub client not configured.", None

        try:
            github_issue = self.github_client.get_issue(github_issue_number)

            # Find existing local issue
            local_issue = None
            for issue in self.core.list_issues():
                if issue.github_issue == github_issue_number:
                    local_issue = issue
                    break

            # If conflict checking is enabled and local issue exists, check for conflicts
            if check_conflicts and local_issue:
                conflict = self.sync_strategy.detect_issue_conflict(
                    local_issue, github_issue
                )
                if conflict:
                    resolution = self.sync_strategy.resolve_conflict(conflict)
                    if resolution == "use_local":
                        return (
                            False,
                            "Conflict detected: Local version is newer. Use push to send local changes.",
                            local_issue,
                        )
                    elif resolution == "skip":
                        return (
                            False,
                            "Conflict detected: Skipping update due to sync strategy.",
                            local_issue,
                        )
                    # If "use_remote", continue with update

            # Extract data from GitHub issue
            title = github_issue["title"]
            content = github_issue["body"] or ""

            # Extract priority and status from labels
            labels = github_issue["labels"]
            priority = self.github_client.labels_to_priority(labels) or Priority.MEDIUM
            status = self.github_client.labels_to_status(labels) or Status.TODO

            # Override status based on GitHub issue state
            if github_issue["state"] == "closed":
                status = Status.DONE

            # Extract milestone
            milestone = ""
            if github_issue["milestone"]:
                milestone = github_issue["milestone"]["title"]

            # Extract assignee
            assignee = ""
            if github_issue["assignee"]:
                assignee = github_issue["assignee"]["login"]

            # Extract other labels (non-priority/status)
            other_labels = []
            for label in labels:
                label_name = label["name"]
                if not (
                    label_name.startswith("priority:")
                    or label_name.startswith("status:")
                ):
                    other_labels.append(label_name)

            if local_issue:
                # Update existing issue
                local_issue.title = title
                local_issue.content = content
                local_issue.priority = priority
                local_issue.status = status
                local_issue.milestone = milestone
                local_issue.assignee = assignee
                local_issue.labels = other_labels
                local_issue.updated = datetime.now()

                issue_path = self.core.issues_dir / local_issue.filename
                IssueParser.save_issue_file(local_issue, issue_path)

                return True, f"Updated local issue {local_issue.id}", local_issue
            else:
                # Create new issue
                new_issue = Issue(
                    title=title,
                    content=content,
                    priority=priority,
                    status=status,
                    milestone=milestone,
                    assignee=assignee,
                    labels=other_labels,
                    github_issue=github_issue_number,
                )

                issue_path = self.core.issues_dir / new_issue.filename
                IssueParser.save_issue_file(new_issue, issue_path)

                return True, f"Created local issue {new_issue.id}", new_issue

        except GitHubAPIError as e:
            return False, f"Failed to pull GitHub issue: {e}", None

    def push_milestone(
        self, milestone: Milestone, check_conflicts: bool = False
    ) -> tuple[bool, str, int | None]:
        """Push a local milestone to GitHub with optional conflict detection."""
        if not self.github_client:
            return False, "GitHub client not configured.", None

        try:
            # Check if milestone already exists on GitHub
            if milestone.github_milestone:
                # If conflict checking is enabled, check for conflicts first
                if check_conflicts:
                    try:
                        github_milestone = self.github_client.get_milestone(
                            milestone.github_milestone
                        )
                        conflict = self.sync_strategy.detect_milestone_conflict(
                            milestone, github_milestone
                        )

                        if conflict:
                            resolution = self.sync_strategy.resolve_conflict(conflict)
                            if resolution == "use_remote":
                                return (
                                    False,
                                    "Conflict detected: Remote version is newer. Use pull to get remote changes.",
                                    None,
                                )
                            elif resolution == "skip":
                                return (
                                    False,
                                    "Conflict detected: Skipping update due to sync strategy.",
                                    None,
                                )
                            # If "use_local", continue with update
                    except GitHubAPIError:
                        # If we can't get the GitHub milestone, proceed with update
                        pass

                return self.update_github_milestone(milestone)

            # Create new GitHub milestone
            state = "closed" if milestone.status == MilestoneStatus.CLOSED else "open"

            github_milestone = self.github_client.create_milestone(
                title=milestone.name,
                description=milestone.description,
                due_date=milestone.due_date,
                state=state,
            )

            # Update local milestone with GitHub milestone number
            milestone.github_milestone = github_milestone["number"]
            milestone.updated = datetime.now()

            # Save updated milestone
            milestone_path = self.core.milestones_dir / milestone.filename
            MilestoneParser.save_milestone_file(milestone, milestone_path)

            return (
                True,
                f"Created GitHub milestone #{github_milestone['number']}",
                github_milestone["number"],
            )

        except GitHubAPIError as e:
            return False, f"Failed to create GitHub milestone: {e}", None

    def update_github_milestone(
        self, milestone: Milestone
    ) -> tuple[bool, str, int | None]:
        """Update an existing GitHub milestone."""
        if not self.github_client or not milestone.github_milestone:
            return False, "GitHub client not configured or milestone not linked.", None

        try:
            state = "closed" if milestone.status == MilestoneStatus.CLOSED else "open"

            github_milestone = self.github_client.update_milestone(
                milestone_number=milestone.github_milestone,
                title=milestone.name,
                description=milestone.description,
                due_date=milestone.due_date,
                state=state,
            )

            # Update local milestone timestamp
            milestone.updated = datetime.now()
            milestone_path = self.core.milestones_dir / milestone.filename
            MilestoneParser.save_milestone_file(milestone, milestone_path)

            return (
                True,
                f"Updated GitHub milestone #{milestone.github_milestone}",
                milestone.github_milestone,
            )

        except GitHubAPIError as e:
            return False, f"Failed to update GitHub milestone: {e}", None

    def _find_github_milestone(self, milestone_name: str) -> int | None:
        """Find GitHub milestone number by name."""
        if not self.github_client:
            return None

        try:
            milestones = self.github_client.get_milestones(state="all")
            for milestone in milestones:
                if milestone["title"] == milestone_name:
                    return milestone["number"]
        except GitHubAPIError:
            pass

        return None

    def _close_remote_orphaned_issues(self) -> tuple[int, int, list[str]]:
        """Close remote GitHub issues that were created by roadmap but no longer exist locally.

        Returns:
            Tuple of (closed_count, error_count, error_messages)
        """
        closed_count = 0
        error_count = 0
        error_messages: list[str] = []

        if not self.github_client:
            return closed_count, error_count, ["GitHub client not configured."]

        try:
            github_issues = self.github_client.get_issues(state="open")
            for gh in github_issues:
                # Only consider issues actually created by roadmap CLI (footer marker)
                body = gh.get("body") or ""
                if "*Created by roadmap CLI*" not in body:
                    continue

                gh_number = gh.get("number")
                if gh_number is None:
                    error_count += 1
                    error_messages.append(
                        f"GitHub issue missing number field: {gh.get('title', 'Unknown')}"
                    )
                    continue

                # Determine if a local issue references this GitHub issue
                found_local = False
                for local in self.core.list_issues():
                    if local.github_issue == gh_number:
                        found_local = True
                        break

                if not found_local:
                    # Close the remote GitHub issue
                    try:
                        # Normalize assignee to a login string if GitHub returns a user object
                        assignees_list = []
                        gh_assignee = gh.get("assignee")
                        if gh_assignee:
                            # GitHub may return an assignee object or a login string
                            if isinstance(gh_assignee, dict):
                                login = gh_assignee.get("login")
                                if login:
                                    assignees_list = [login]
                            elif isinstance(gh_assignee, str):
                                assignees_list = [gh_assignee]

                        self.github_client.update_issue(
                            issue_number=gh_number,
                            title=gh.get("title", ""),
                            body=body
                            + "\n\n(Closed by roadmap CLI due to missing local issue)",
                            state="closed",
                            labels=[l["name"] for l in gh.get("labels", [])],
                            assignees=assignees_list,
                            milestone=None,
                        )
                        closed_count += 1
                    except GitHubAPIError as e:
                        error_count += 1
                        error_messages.append(
                            f"Failed to close issue #{gh_number}: {e}"
                        )

        except GitHubAPIError as e:
            error_count += 1
            error_messages.append(f"Failed to list GitHub issues: {e}")

        return closed_count, error_count, error_messages

    def sync_all_issues(self, direction: str = "push") -> tuple[int, int, list[str]]:
        """Sync all issues between local and GitHub.

        Args:
            direction: "push" to send local to GitHub, "pull" to get from GitHub

        Returns:
            Tuple of (success_count, error_count, error_messages)
        """
        success_count = 0
        error_count = 0
        error_messages = []

        if direction == "push":
            issues = self.core.list_issues()
            for issue in issues:
                success, message, _ = self.push_issue(issue)
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    error_messages.append(f"{issue.title}: {message}")

            # Optionally detect local deletions and close remote orphaned issues.
            # This is an opt-in feature controlled by config.sync.close_orphaned
            # to avoid surprising behavior during default syncs and in tests.
            try:
                close_orphans = bool(self.config.sync.get("close_orphaned", False))
            except Exception:
                close_orphans = False

            if close_orphans and self.github_client:
                try:
                    closed, close_errors, close_msgs = (
                        self._close_remote_orphaned_issues()
                    )
                    success_count += closed
                    error_count += close_errors
                    error_messages.extend(close_msgs)
                except Exception as e:
                    error_count += 1
                    error_messages.append(
                        f"Failed checking remote orphaned issues: {e}"
                    )

        elif direction == "pull":
            if not self.github_client:
                return 0, 1, ["GitHub client not configured."]

            try:
                github_issues = self.github_client.get_issues(state="all")
                for github_issue in github_issues:
                    # Skip pull requests (they appear in issues API)
                    if "pull_request" in github_issue:
                        continue

                    success, message, _ = self.pull_issue(github_issue["number"])
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        error_messages.append(
                            f"Issue #{github_issue['number']}: {message}"
                        )

            except GitHubAPIError as e:
                error_count += 1
                error_messages.append(f"Failed to get GitHub issues: {e}")

        return success_count, error_count, error_messages

    def sync_all_milestones(
        self, direction: str = "push"
    ) -> tuple[int, int, list[str]]:
        """Sync all milestones between local and GitHub.

        Args:
            direction: "push" to send local to GitHub, "pull" to get from GitHub

        Returns:
            Tuple of (success_count, error_count, error_messages)
        """
        success_count = 0
        error_count = 0
        error_messages = []

        if direction == "push":
            milestones = self.core.list_milestones()
            for milestone in milestones:
                success, message, _ = self.push_milestone(milestone)
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    error_messages.append(f"{milestone.name}: {message}")

        elif direction == "pull":
            if not self.github_client:
                return 0, 1, ["GitHub client not configured."]

            try:
                github_milestones = self.github_client.get_milestones(state="all")
                for github_milestone in github_milestones:
                    # Create or update local milestone
                    local_milestone = self.core.get_milestone(github_milestone["title"])

                    if local_milestone:
                        # Update existing
                        local_milestone.description = (
                            github_milestone["description"] or ""
                        )
                        local_milestone.github_milestone = github_milestone["number"]
                        if github_milestone["due_on"]:
                            local_milestone.due_date = (
                                self.sync_strategy._parse_github_timestamp(
                                    github_milestone["due_on"]
                                )
                            )
                        local_milestone.status = (
                            MilestoneStatus.CLOSED
                            if github_milestone["state"] == "closed"
                            else MilestoneStatus.OPEN
                        )
                        local_milestone.updated = datetime.now()

                        milestone_path = (
                            self.core.milestones_dir / local_milestone.filename
                        )
                        MilestoneParser.save_milestone_file(
                            local_milestone, milestone_path
                        )
                        success_count += 1
                    else:
                        # Create new
                        due_date = None
                        if github_milestone["due_on"]:
                            due_date = self.sync_strategy._parse_github_timestamp(
                                github_milestone["due_on"]
                            )

                        new_milestone = Milestone(
                            name=github_milestone["title"],
                            description=github_milestone["description"] or "",
                            due_date=due_date,
                            status=(
                                MilestoneStatus.CLOSED
                                if github_milestone["state"] == "closed"
                                else MilestoneStatus.OPEN
                            ),
                            github_milestone=github_milestone["number"],
                        )

                        milestone_path = (
                            self.core.milestones_dir / new_milestone.filename
                        )
                        MilestoneParser.save_milestone_file(
                            new_milestone, milestone_path
                        )
                        success_count += 1

            except GitHubAPIError as e:
                error_count += 1
                error_messages.append(f"Failed to get GitHub milestones: {e}")

        return success_count, error_count, error_messages

    def bidirectional_sync(
        self, sync_issues: bool = True, sync_milestones: bool = True
    ) -> tuple[int, int, list[str], list[SyncConflict]]:
        """Perform intelligent bidirectional synchronization between local and GitHub.

        This method:
        1. Compares local and remote items
        2. Detects conflicts based on timestamps
        3. Resolves conflicts using the sync strategy
        4. Syncs in both directions as needed

        Args:
            sync_issues: Whether to sync issues
            sync_milestones: Whether to sync milestones

        Returns:
            Tuple of (success_count, error_count, error_messages, conflicts_detected)
        """
        if not self.github_client:
            return 0, 1, ["GitHub client not configured."], []

        total_success = 0
        total_errors = 0
        all_errors = []
        all_conflicts = []

        try:
            # Sync issues bidirectionally
            if sync_issues:
                success, errors, error_msgs, conflicts = (
                    self._bidirectional_sync_issues()
                )
                total_success += success
                total_errors += errors
                all_errors.extend(error_msgs)
                all_conflicts.extend(conflicts)

            # Sync milestones bidirectionally
            if sync_milestones:
                success, errors, error_msgs, conflicts = (
                    self._bidirectional_sync_milestones()
                )
                total_success += success
                total_errors += errors
                all_errors.extend(error_msgs)
                all_conflicts.extend(conflicts)

        except Exception as e:
            total_errors += 1
            all_errors.append(f"Bidirectional sync failed: {e}")

        return total_success, total_errors, all_errors, all_conflicts

    def _bidirectional_sync_issues(
        self,
    ) -> tuple[int, int, list[str], list[SyncConflict]]:
        """Perform bidirectional sync for issues."""
        success_count = 0
        error_count = 0
        error_messages = []
        conflicts = []

        try:
            if not self.github_client:
                return (
                    success_count,
                    error_count + 1,
                    ["GitHub client not configured."],
                    conflicts,
                )

            # Get all local issues and GitHub issues
            local_issues = {
                issue.github_issue: issue
                for issue in self.core.list_issues()
                if issue.github_issue
            }
            local_issues_no_github = [
                issue for issue in self.core.list_issues() if not issue.github_issue
            ]

            github_issues = self.github_client.get_issues(state="all")
            github_issues_dict = {
                issue["number"]: issue
                for issue in github_issues
                if "pull_request" not in issue
            }

            # Sync existing linked issues (potential conflicts)
            for github_number, local_issue in local_issues.items():
                if github_number in github_issues_dict:
                    github_issue = github_issues_dict[github_number]

                    # Check for conflicts
                    conflict = self.sync_strategy.detect_issue_conflict(
                        local_issue, github_issue
                    )
                    if conflict:
                        conflicts.append(conflict)
                        resolution = self.sync_strategy.resolve_conflict(conflict)

                        if resolution == "use_local":
                            # Push local to GitHub
                            success, message, _ = self.push_issue(
                                local_issue, check_conflicts=False
                            )
                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                                error_messages.append(
                                    f"Push {local_issue.title}: {message}"
                                )
                        elif resolution == "use_remote":
                            # Pull from GitHub
                            success, message, _ = self.pull_issue(
                                github_number, check_conflicts=False
                            )
                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                                error_messages.append(
                                    f"Pull issue #{github_number}: {message}"
                                )
                        # If "skip", do nothing
                    else:
                        # No conflict - sync normally (should be in sync already)
                        success_count += 1

            # Push local issues that don't exist on GitHub
            for local_issue in local_issues_no_github:
                success, message, github_number = self.push_issue(
                    local_issue, check_conflicts=False
                )
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    error_messages.append(f"Push new {local_issue.title}: {message}")

            # Pull GitHub issues that don't exist locally
            for github_number, github_issue in github_issues_dict.items():
                if github_number not in local_issues:
                    success, message, _ = self.pull_issue(
                        github_number, check_conflicts=False
                    )
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        error_messages.append(
                            f"Pull new issue #{github_number}: {message}"
                        )

        except GitHubAPIError as e:
            error_count += 1
            error_messages.append(f"Failed to sync issues: {e}")

        return success_count, error_count, error_messages, conflicts

    def _bidirectional_sync_milestones(
        self,
    ) -> tuple[int, int, list[str], list[SyncConflict]]:
        """Perform bidirectional sync for milestones."""
        success_count = 0
        error_count = 0
        error_messages = []
        conflicts = []

        try:
            # Get all local milestones and GitHub milestones
            local_milestones = {
                ms.github_milestone: ms
                for ms in self.core.list_milestones()
                if ms.github_milestone
            }
            local_milestones_no_github = [
                ms for ms in self.core.list_milestones() if not ms.github_milestone
            ]

            if not self.github_client:
                return (
                    success_count,
                    error_count + 1,
                    ["GitHub client not configured."],
                    conflicts,
                )

            github_milestones = self.github_client.get_milestones(state="all")
            github_milestones_dict = {ms["number"]: ms for ms in github_milestones}

            # Sync existing linked milestones (potential conflicts)
            for github_number, local_milestone in local_milestones.items():
                if github_number in github_milestones_dict:
                    github_milestone = github_milestones_dict[github_number]

                    # Check for conflicts
                    conflict = self.sync_strategy.detect_milestone_conflict(
                        local_milestone, github_milestone
                    )
                    if conflict:
                        conflicts.append(conflict)
                        resolution = self.sync_strategy.resolve_conflict(conflict)

                        if resolution == "use_local":
                            # Push local to GitHub
                            success, message, _ = self.push_milestone(
                                local_milestone, check_conflicts=False
                            )
                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                                error_messages.append(
                                    f"Push {local_milestone.name}: {message}"
                                )
                        elif resolution == "use_remote":
                            # Update local from GitHub
                            local_milestone.description = (
                                github_milestone["description"] or ""
                            )
                            if github_milestone["due_on"]:
                                local_milestone.due_date = (
                                    self.sync_strategy._parse_github_timestamp(
                                        github_milestone["due_on"]
                                    )
                                )
                            else:
                                local_milestone.due_date = None
                            local_milestone.status = (
                                MilestoneStatus.CLOSED
                                if github_milestone["state"] == "closed"
                                else MilestoneStatus.OPEN
                            )
                            local_milestone.updated = datetime.now()

                            milestone_path = (
                                self.core.milestones_dir / local_milestone.filename
                            )
                            MilestoneParser.save_milestone_file(
                                local_milestone, milestone_path
                            )
                            success_count += 1
                        # If "skip", do nothing
                    else:
                        # No conflict - should be in sync already
                        success_count += 1

            # Push local milestones that don't exist on GitHub
            for local_milestone in local_milestones_no_github:
                success, message, github_number = self.push_milestone(
                    local_milestone, check_conflicts=False
                )
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    error_messages.append(f"Push new {local_milestone.name}: {message}")

            # Create local milestones for GitHub milestones that don't exist locally
            for github_number, github_milestone in github_milestones_dict.items():
                if github_number not in local_milestones:
                    # Create new local milestone
                    due_date = None
                    if github_milestone["due_on"]:
                        due_date = self.sync_strategy._parse_github_timestamp(
                            github_milestone["due_on"]
                        )

                    new_milestone = Milestone(
                        name=github_milestone["title"],
                        description=github_milestone["description"] or "",
                        due_date=due_date,
                        status=(
                            MilestoneStatus.CLOSED
                            if github_milestone["state"] == "closed"
                            else MilestoneStatus.OPEN
                        ),
                        github_milestone=github_milestone["number"],
                    )

                    milestone_path = self.core.milestones_dir / new_milestone.filename
                    MilestoneParser.save_milestone_file(new_milestone, milestone_path)
                    success_count += 1

        except GitHubAPIError as e:
            error_count += 1
            error_messages.append(f"Failed to sync milestones: {e}")

        return success_count, error_count, error_messages, conflicts
